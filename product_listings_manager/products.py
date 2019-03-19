# koji hub plugin

import copy
import koji
import logging
import pgdb
import re

dbname = None  # eg. "compose"
dbhost = None  # eg "db.example.com"
dbuser = None  # eg. "myuser"
dbpasswd = None  # eg. "mypassword"

logger = logging.getLogger(__name__)


def get_koji_session():
    """
    Get a koji session for accessing kojihub functions.
    """
    conf = koji.read_config('brew')
    hub = conf['server']
    return koji.ClientSession(hub, {})


def get_build(nvr, session=None):
    """
    Get a build from kojihub.
    """
    if session is None:
        session = get_koji_session()

    try:
        build = session.getBuild(nvr, strict=True)
    except koji.GenericError as ex:
        raise ProductListingsNotFoundError(str(ex))

    logger.debug('Build info: {}'.format(build))
    return build


class ProductListingsNotFoundError(ValueError):
    pass


class Products(object):
    """
    Class to hold methods related to product information.
    """
    all_release_types = [re.compile(r"^TEST\d*", re.I),
                         re.compile(r"^ALPHA\d*", re.I),
                         re.compile(r"^BETA\d*", re.I),
                         re.compile(r"^RC\d*", re.I),
                         re.compile(r"^GOLD", re.I),
                         re.compile(r"^U\d+(-beta)?$", re.I)]

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

    def execute_query(dbh, query, **kwargs):
        dbh.execute(query, kwargs)
    execute_query = staticmethod(execute_query)

    def get_product_info(compose_dbh, product):
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, """
            SELECT version, variant
            FROM products
            WHERE label = %(product)s""", product=product)
        products = dbc.fetchall()
        versions = [x[0] for x in products]
        versions.sort(Products.my_sort)
        versions.reverse()

        if not versions:
            raise ProductListingsNotFoundError("Could not find a product with label: %s" % product)

        return (versions[0], [x[1] for x in products if x[0] == versions[0]])
    get_product_info = staticmethod(get_product_info)

    def get_overrides(compose_dbh, product, version, variant=None):
        '''Returns the list of package overrides for the particular product specified.'''

        qargs = dict(product=product, version=version)
        if variant:
            variant_clause = "products.variant = %(variant)s"
            qargs['variant'] = variant
        else:
            variant_clause = "products.variant is NULL"

        qry = """
            SELECT name, pkg_arch, product_arch, include
            FROM overrides
            WHERE product IN (
                SELECT id
                FROM products
                WHERE label = %(product)s
                AND version = %(version)s
                AND """ + variant_clause + """
            )
            """

        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, qry, **qargs)
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
        Products.execute_query(dbc, """
            SELECT name
            FROM match_versions
            WHERE product = %(product)s
            """, product=product)
        rows = dbc.fetchall()
        matches = []
        for row in rows:
            matches.append(row[0])
        return matches
    get_match_versions = staticmethod(get_match_versions)

    def get_srconly_flag(compose_dbh, product, version):
        '''BREW-260 - Returns allow_source_only field for the product and matching version.'''
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, """
            SELECT allow_source_only
            FROM products
            WHERE label = %(product)s
            AND version = %(version)s
            """, product=product, version=version)
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

        qargs = dict(product=product, version=version)
        if variant:
            variant_clause = "products.variant = %(variant)s"
            qargs['variant'] = variant
        else:
            variant_clause = "products.variant is NULL"

        qry = """
            SELECT trees.id, arch, compatlayer
            FROM trees, products, tree_product_map
            WHERE imported = 1
            AND trees.id = tree_product_map.tree_id
            AND products.id = tree_product_map.product_id
            AND products.label = %(product)s
            AND products.version = %(version)s
            AND """ + variant_clause + """
            order by date desc, id desc
            """

        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, qry, **qargs)

        rows = dbc.fetchall()
        trees = {}
        compat_trees = {}
        for row in rows:
            id = row[0]
            arch = row[1]
            if row[2]:
                if arch not in compat_trees:
                    compat_trees[arch] = id
            else:
                if arch not in trees:
                    trees[arch] = id
        return trees.values() + compat_trees.values()
    precalc_treelist = staticmethod(precalc_treelist)

    def dest_get_archs(compose_dbh, trees, src_arch, names, cache_entry, version=None, overrides=None):
        '''Return a list of arches that this package/arch combination ships on.'''

        if trees is None:
            return dict((name, src_arch) for name in names)

        dbc = compose_dbh.cursor()
        qry = """
            SELECT DISTINCT trees.arch, packages.name
            FROM trees, packages, tree_packages
            WHERE trees.imported = 1 and trees.id = tree_packages.trees_id
            AND packages.id = tree_packages.packages_id
            AND packages.arch = %(arch)s
            """

        if pgdb.version.startswith('4'):
            # backwards compatibility with pygresql 4 in eng-rhel-7
            qry += """
                AND packages.name IN %(names)s
                AND trees.id IN %(trees)s
                """
        else:
            qry += """
                AND packages.name = ANY(%(names)s)
                AND trees.id = ANY(%(trees)s)
                """

        qargs = dict(arch=src_arch, names=names, trees=trees)
        if version:
            qry += " AND packages.version = %(version)s"
            qargs['version'] = version
        Products.execute_query(dbc, qry, **qargs)
        ret = {}
        while 1:
            arow = dbc.fetchone()
            if not arow:
                break
            ret.setdefault(arow[1], {}).setdefault(arow[0], 1)
        for name in names:
            # use cached map entry if there are no records from treetables
            if koji.is_debuginfo(name) and not ret.get(name, {}):
                ret[name] = copy.deepcopy(cache_entry)

            if overrides and name in overrides and src_arch in overrides[name] and not version:
                for tree_arch, include in overrides[name][src_arch].items():
                    if include:
                        ret.setdefault(name, {}).setdefault(tree_arch, 1)
                    elif name in ret and tree_arch in ret[name]:
                        del ret[name][tree_arch]
        return ret
    dest_get_archs = staticmethod(dest_get_archs)

    def compose_get_dbh():
        # Database settings
        return pgdb.connect(database=dbname, host=dbhost, user=dbuser, password=dbpasswd)
    compose_get_dbh = staticmethod(compose_get_dbh)

    def get_module(compose_dbh, name, stream):
        qargs = dict(name=name, stream=stream)
        qry = """
            SELECT id
            FROM modules
            WHERE name = %(name)s
            AND stream = %(stream)s
            ORDER BY version DESC
            """
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, qry, **qargs)
        module = dbc.fetchone()
        return module
    get_module = staticmethod(get_module)

    def precalc_module_trees(compose_dbh, product, version, module_id, variant=None):
        '''Returns dict {tree_id: arch}.

        Looks in the compose db for a list of trees (one per arch) that are the most
        recent for the particular product specified.'''

        qargs = dict(product=product, version=version, module_id=module_id)
        if variant:
            variant_clause = "products.variant = %(variant)s"
            qargs['variant'] = variant
        else:
            variant_clause = "products.variant is NULL"

        qry = """
            SELECT trees.id, arch
            FROM trees, products, tree_product_map, tree_modules
            WHERE imported = 1
            AND trees.id = tree_product_map.tree_id
            AND products.id = tree_product_map.product_id
            AND tree_modules.trees_id = trees.id
            AND tree_modules.modules_id = %(module_id)d
            AND products.label = %(product)s
            AND products.version = %(version)s
            AND """ + variant_clause + """
            order by date desc, id desc
            """
        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, qry, **qargs)

        rows = dbc.fetchall()
        return {tree_id: arch for tree_id, arch in reversed(rows)}
    precalc_module_trees = staticmethod(precalc_module_trees)

    def get_module_overrides(compose_dbh, product, version, module_name, module_stream, variant=None):
        '''Returns the list of module overrides for the particular product specified.'''

        qargs = dict(product=product, version=version, module_name=module_name, module_stream=module_stream)
        if variant:
            variant_clause = "products.variant = %(variant)s"
            qargs['variant'] = variant
        else:
            variant_clause = "products.variant is NULL"

        qry = """
            SELECT product_arch
            FROM module_overrides, products, trees, tree_product_map
            WHERE products.label = %(product)s
            AND products.version = %(version)s
            AND module_overrides.name = %(module_name)s
            AND module_overrides.stream = %(module_stream)s
            AND module_overrides.product = products.id
            AND tree_product_map.product_id = products.id
            AND tree_product_map.tree_id = trees.id
            AND """ + variant_clause

        dbc = compose_dbh.cursor()
        Products.execute_query(dbc, qry, **qargs)
        rows = dbc.fetchall()

        return [row[0] for row in rows]
    get_module_overrides = staticmethod(get_module_overrides)


def getProductInfo(label):
    """
    Get a list of the versions and variants of a product with the given label.
    """
    return Products.get_product_info(Products.compose_get_dbh(), label)


def getProductListings(productLabel, buildInfo):
    """
    Get a map of which variants of the given product included packages built
    by the given build, and which arches each variant included.
    """
    compose_dbh = Products.compose_get_dbh()

    session = get_koji_session()
    build = get_build(buildInfo, session)

    rpms = session.listRPMs(buildID=build['id'])
    if not rpms:
        raise ProductListingsNotFoundError("Could not find any RPMs for build: %s" % buildInfo)

    # sort rpms, so first part of list consists of sorted 'normal' rpms and
    # second part are sorted debuginfos
    debuginfos = [x for x in rpms if '-debuginfo' in x['nvr']]
    base_rpms = [x for x in rpms if '-debuginfo' not in x['nvr']]
    rpms = sorted(base_rpms, key=lambda x: x['nvr']) + sorted(debuginfos, key=lambda x: x['nvr'])
    srpm = "%(package_name)s-%(version)s-%(release)s.src.rpm" % build

    prodinfo = Products.get_product_info(compose_dbh, productLabel)
    version, variants = prodinfo

    listings = {}
    match_version = Products.get_match_versions(compose_dbh, productLabel)
    for variant in variants:
        if variant is None:
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
            d[arch] = Products.dest_get_archs(
                compose_dbh, treelist,
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
            d[arch] = Products.dest_get_archs(
                compose_dbh, treelist,
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
            # BREW-260: Read allow_src_only flag for the product/version
            allow_src_only = Products.get_srconly_flag(compose_dbh, productLabel, version)
            if len(nvrs) == 1:
                maps = listings[variant][nvrs[0]].keys()
                # BREW-260: check for allow_src_only flag added
                if len(maps) == 1 and maps[0] == 'src' and not allow_src_only:
                    del listings[variant]
    return listings


def getModuleProductListings(productLabel, moduleNVR):
    """
    Get a map of which variants of the given product included the given module,
    and which arches each variant included.
    """
    compose_dbh = Products.compose_get_dbh()

    build = get_build(moduleNVR)
    try:
        module = build['extra']['typeinfo']['module']
        module_name = module['name']
        module_stream = module['stream']
    except (KeyError, TypeError):
        raise ProductListingsNotFoundError("It's not a module build: %s" % moduleNVR)

    prodinfo = Products.get_product_info(compose_dbh, productLabel)
    version, variants = prodinfo

    module = Products.get_module(compose_dbh, module_name, module_stream)
    if not module:
        raise ProductListingsNotFoundError("Could not find a module build with NVR: %s" % moduleNVR)
    module_id = module[0]

    listings = {}
    for variant in variants:
        if variant is None:
            # dict keys must be a string
            variant = ''
        trees = Products.precalc_module_trees(compose_dbh, productLabel, version, module_id, variant)

        overrides = Products.get_module_overrides(
            compose_dbh, productLabel, version, module_name, module_stream, variant)

        archs = sorted(set(trees.values() + overrides))

        if archs:
            listings.setdefault(variant, archs)

    return listings
