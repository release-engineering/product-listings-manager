#koji hub plugin

from koji.context import context
from koji.plugin import export
import koji
import pgdb
import re
import sys
import instance.config

class Products(object):
    """
    Class to hold methods related to product information.
    """
    all_release_types = [ re.compile("^TEST\d*", re.I),
                          re.compile("^ALPHA\d*", re.I),
                          re.compile("^BETA\d*", re.I),
                          re.compile("^RC\d*", re.I),
                          re.compile("^GOLD", re.I),
                          re.compile("^U\d+(-beta)?$", re.I) ]

    def score(release):
        map = Products.all_release_types
        i = len(map) - 1
        while i >= 0:
            if map[i].search(release):
                return i
            i = i - 1
        return i
    score = staticmethod(score)

    def my_sort(x, y):
        if len(x) > len(y) and y == x[:len(y)]:
            return -1
        if len(y) > len(x) and x == y[:len(x)]:
            return 1
        x_score = Products.score(x)
        y_score = Products.score(y)
        if x_score == y_score:
            return cmp(x, y)
        else:
            return cmp(x_score, y_score)
    my_sort = staticmethod(my_sort)

    def execute_query(dbh, query, args=None):
        if args:
            dbh.execute(query, args)
        else:
            dbh.execute(query)
    execute_query = staticmethod(execute_query)

    def get_product_info(compose_dbh, product):
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, """
        SELECT version, variant
        FROM products
        WHERE label = '%s'""" % product)
        products = dbc.fetchall()
        versions = [x[0] for x in products]
        versions.sort(Products.my_sort)
        versions.reverse()

        if versions:
            return (versions[0], [x[1] for x in products if x[0] == versions[0]])
        else:
            return None
    get_product_info = staticmethod(get_product_info)

    def get_overrides(compose_dbh, product, version, variant=None):
        '''Returns the list of package overrides for the particular product specified.'''
        if variant:
            variant_clause = "products.variant = '%s'" % variant
        else:
            variant_clause = "products.variant is NULL"
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, """
        SELECT name, pkg_arch, product_arch, include
        FROM overrides
        WHERE product IN ( SELECT id FROM products WHERE label = '%s' and version = '%s' and %s )
        """ % (product, version, variant_clause))
        rows = dbc.fetchall()
        overrides = {}
        for row in rows:
            name, pkg_arch, product_arch, include = row[0:4]
            overrides.setdefault(name, {}).setdefault(pkg_arch, {}).setdefault(product_arch, include)
        return overrides
    get_overrides = staticmethod(get_overrides)

    def get_match_versions(compose_dbh, product):
        '''Returns the list of packages for this product where we must match the version.'''
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, """SELECT name FROM match_versions WHERE product = '%s'""" % product)
        rows = dbc.fetchall()
        matches = []
        for row in rows:
            matches.append(row[0])
        return matches
    get_match_versions = staticmethod(get_match_versions)

    def get_srconly_flag(compose_dbh, product, version):
        '''BREW-260 - Returns allow_source_only field for the product and matching version.'''
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, """SELECT allow_source_only FROM products WHERE label = '%s' and version = '%s'""" % (product,version))
        rows = dbc.fetchall()
        for (allow_source_only,) in rows:
            if allow_source_only:
                return True
        return False
    get_srconly_flag = staticmethod(get_srconly_flag)

    def precalc_treelist(compose_dbh, product, version, variant=None):
        '''Returns the list of trees to consider.

        Looks in the compose db for a list of trees (one per arch) that are the most
        recent for the particular product specified.'''

        if variant:
            variant_clause = "products.variant = '%s'" % variant
        else:
            variant_clause = "products.variant is NULL"
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, """
        SELECT trees.id, arch, compatlayer
        FROM trees, products, tree_product_map
        WHERE imported = 1
        and trees.id = tree_product_map.tree_id
        and products.id = tree_product_map.product_id
        and products.label = '%s'
        and products.version = '%s'
        and %s
        order by date desc, id desc
        """ % (product, version, variant_clause))
        rows = dbc.fetchall()
        trees = {}
        compat_trees = {}
        for row in rows:
            id = row[0]
            arch = row[1]
            if row[2]:
                if not compat_trees.has_key(arch):
                    compat_trees[arch] = id
            else:
                if not trees.has_key(arch):
                    trees[arch] = id
        return trees.values() + compat_trees.values()
    precalc_treelist = staticmethod(precalc_treelist)

    def dest_get_archs(compose_dbh, trees, src_arch, names, cache_entry, version=None, overrides=None):
        '''Return a list of arches that this package/arch combination ships on.'''

        if trees is None:
            return dict((name, src_arch) for name in names)

        dbc = compose_dbh.cursor()
        qry = "SELECT DISTINCT trees.arch, packages.name FROM trees, packages, tree_packages WHERE trees.imported = 1 and trees.id = tree_packages.trees_id AND packages.id = tree_packages.packages_id AND packages.arch = %s AND packages.name IN %s AND trees.id IN %s"
        qargs = [src_arch, names, trees]
        if version:
            qry += " AND packages.version = %s"
            qargs.append(version)
        Products.execute_query(dbc, qry, qargs)
        ret = {}
        while 1:
            arow = dbc.fetchone()
            if not arow:
                break
            ret.setdefault(arow[1], {}).setdefault(arow[0], 1)
        for name in names:
            # use cached map entry if there are no records from treetables
            if koji.is_debuginfo(name) and not ret.get(name, {}):
                ret[name] = cache_entry

            if overrides and overrides.has_key(name) and overrides[name].has_key(src_arch) and not version:
                for tree_arch, include in overrides[name][src_arch].items():
                    if include:
                        ret.setdefault(name, {}).setdefault(tree_arch, 1)
                    elif ret.has_key(tree_arch):
                        del ret[name][tree_arch]
        return ret
    dest_get_archs = staticmethod(dest_get_archs)

    def compose_get_dbh():
        # Database settings
        dbname = instance.config.dbname
        dbhost = instance.config.dbhost
        dbuser = instance.config.dbuser
        dbpasswd = instance.config.dbpasswd
        return pgdb.connect(database=dbname, host=dbhost, user=dbuser, password=dbpasswd)
    compose_get_dbh = staticmethod(compose_get_dbh)

    def mysort(x, y):
        if x[0].find("-debuginfo") > -1:
            if y[0].find("-debuginfo") == -1:
                return 1
            else:
                return cmp(x[0], y[0])
        if y[0].find("-debuginfo") == -1:
            return cmp(x[0], y[0])
        else:
            return -1
    mysort = staticmethod(mysort)

@export
def getProductInfo(label):
    """
    Get a list of the versions and variants of a product with the given label.
    """
    return Products.get_product_info(Products.compose_get_dbh(), label)

@export
def getProductListings(productLabel, buildInfo):
    """
    Get a map of which variants of the given product included packages built
    by the given build, and which arches each variant included.
    """
    compose_dbh = Products.compose_get_dbh()

    #XXX - need access to hub kojihub functions
    build = context.handlers.call('getBuild', buildInfo, strict=True)
    sys.stderr.write("%r" % build)
    sys.stderr.flush()
    rpms = context.handlers.call('listRPMs', buildID=build['id'])
    if not rpms:
        raise koji.GenericError, "Could not find any RPMs for build: %s" % buildInfo

    tmp_list = [ (x['nvr'], x) for x in rpms ]
    tmp_list.sort(Products.mysort)
    rpms = [ x[1] for x in tmp_list ]
    srpm = "%(package_name)s-%(version)s-%(release)s.src.rpm" % build

    prodinfo = Products.get_product_info(compose_dbh, productLabel)
    if not prodinfo:
        # no product with the given label exists
        raise koji.GenericError, "Could not find a product with label: %s" % productLabel
    version, variants = prodinfo

    listings = {}
    match_version = Products.get_match_versions(compose_dbh, productLabel)
    for variant in variants:
        if variant == None:
            # dict keys must be a string
            variant = ''
        treelist = Products.precalc_treelist(compose_dbh, productLabel, version, variant)
        if not treelist:
            continue
        overrides = Products.get_overrides(compose_dbh, productLabel, version, variant)
        cache_map = {}
        for rpm in rpms:
            if rpm['name'] in match_version:
                rpm_version = rpm['version']
            else:
                rpm_version = None

        # without debuginfos
        rpms_nondebug = [rpm for rpm in rpms if not koji.is_debuginfo(rpm['name'])]
        d = {}
        all_archs = set([rpm['arch'] for rpm in rpms_nondebug])
        for arch in all_archs:
            d[arch] = Products.dest_get_archs(compose_dbh, treelist,
                      arch, [rpm['name'] for rpm in rpms_nondebug if rpm['arch'] == arch],
                      cache_map.get(srpm, {}).get(arch, {}),
                      rpm_version, overrides,)

        for rpm in rpms_nondebug:
            dest_archs = d[rpm['arch']].get(rpm['name'], {}).keys()
            if rpm['arch'] != 'src':
                cache_map.setdefault(srpm, {})
                cache_map[srpm].setdefault(rpm['arch'], {})
                for x in dest_archs:
                    cache_map[srpm][rpm['arch']][x] = 1
            for dest_arch in dest_archs:
                listings.setdefault(variant, {}).setdefault(rpm['nvr'], {}).setdefault(rpm['arch'], []).append(dest_arch)

        # debuginfo only
        rpms_debug = [rpm for rpm in rpms if koji.is_debuginfo(rpm['name'])]
        d = {}
        all_archs = set([rpm['arch'] for rpm in rpms_debug])
        for arch in all_archs:
            d[arch] = Products.dest_get_archs(compose_dbh, treelist,
                      arch, [rpm['name'] for rpm in rpms_debug if rpm['arch'] == arch],
                      cache_map.get(srpm, {}).get(arch, {}),
                      rpm_version, overrides,)

        for rpm in rpms_debug:
            dest_archs = d[rpm['arch']].get(rpm['name'], {}).keys()
            if rpm['arch'] != 'src':
                cache_map.setdefault(srpm, {})
                cache_map[srpm].setdefault(rpm['arch'], {})
                for x in dest_archs:
                    cache_map[srpm][rpm['arch']][x] = 1
            for dest_arch in dest_archs:
                listings.setdefault(variant, {}).setdefault(rpm['nvr'], {}).setdefault(rpm['arch'], []).append(dest_arch)

        for variant in listings.keys():
            nvrs = listings[variant].keys()
            #BREW-260: Read allow_src_only flag for the product/version
            allow_src_only = Products.get_srconly_flag(compose_dbh, productLabel, version)
            if len(nvrs) == 1:
                maps = listings[variant][nvrs[0]].keys()
                #BREW-260: check for allow_src_only flag added
                if len(maps) == 1 and maps[0] == 'src' and not allow_src_only:
                    del listings[variant]
    return listings
