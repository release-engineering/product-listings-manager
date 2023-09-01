# koji hub plugin

import copy
import functools
import logging
import re

import koji
from product_listings_manager import models

logger = logging.getLogger(__name__)


def get_koji_session():
    """
    Get a koji session for accessing kojihub functions.
    """
    conf = koji.read_config("brew")
    hub = conf["server"]
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

    logger.debug(f"Build info: {build}")
    return build


class ProductListingsNotFoundError(ValueError):
    pass


def _cmp(a, b):
    # Equivalent for cmp() function in python2
    # https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
    return (a > b) - (a < b)


class Products:
    """
    Class to hold methods related to product information.
    """

    all_release_types = [
        re.compile(r"^TEST\d*", re.I),
        re.compile(r"^ALPHA\d*", re.I),
        re.compile(r"^BETA\d*", re.I),
        re.compile(r"^RC\d*", re.I),
        re.compile(r"^GOLD", re.I),
        re.compile(r"^U\d+(-beta)?$", re.I),
    ]

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
        if len(x) > len(y) and y == x[: len(y)]:
            return -1
        if len(y) > len(x) and x == y[: len(x)]:
            return 1
        x_score = Products.score(x)
        y_score = Products.score(y)
        if x_score == y_score:
            return _cmp(x, y)
        else:
            return _cmp(x_score, y_score)

    my_sort = staticmethod(my_sort)

    def get_product_info(label):
        """Get the latest version of product and it's variants."""
        products = models.Products.query.filter_by(label=label).all()
        versions = [x.version for x in products]
        # Use functools.cmp_to_key for python3
        # https://docs.python.org/3/library/functools.html#functools.cmp_to_key
        versions.sort(key=functools.cmp_to_key(Products.my_sort))
        versions.reverse()

        if not versions:
            raise ProductListingsNotFoundError(
                "Could not find a product with label: %s" % label
            )

        return (
            versions[0],
            [x.variant for x in products if x.version == versions[0]],
        )

    get_product_info = staticmethod(get_product_info)

    def get_overrides(product, version, variant=None):
        """
        Returns the list of package overrides for the particular product specified.
        """

        query = models.Overrides.query.join(
            models.Overrides.productref
        ).filter(
            models.Products.label == product,
            models.Products.version == version,
        )
        if variant:
            query = query.filter(models.Products.variant == variant)

        overrides = {}
        for row in query.all():
            name, pkg_arch, product_arch, include = (
                row.name,
                row.pkg_arch,
                row.product_arch,
                row.include,
            )
            overrides.setdefault(name, {}).setdefault(pkg_arch, {}).setdefault(
                product_arch, include
            )
        return overrides

    get_overrides = staticmethod(get_overrides)

    def get_match_versions(product):
        """
        Returns the list of packages for this product where we must match the version.
        """
        return [
            m.name
            for m in models.MatchVersions.query.filter_by(
                product=product
            ).all()
        ]

    get_match_versions = staticmethod(get_match_versions)

    def get_srconly_flag(product, version):
        """
        BREW-260 - Returns allow_source_only field for the product and matching version.
        """
        q = models.Products.query.filter_by(
            label=product, version=version, allow_source_only=True
        )
        return models.db.session.query(q.exists()).scalar()

    get_srconly_flag = staticmethod(get_srconly_flag)

    def precalc_treelist(product, version, variant=None):
        """Returns the list of trees to consider.

        Looks in the compose db for a list of trees (one per arch) that are the most
        recent for the particular product specified."""

        query = (
            models.Trees.query.join(models.Trees.products)
            .order_by(models.Trees.date.desc(), models.Trees.id.desc())
            .filter(
                models.Products.label == product,
                models.Products.version == version,
            )
        )
        if variant:
            query = query.filter(models.Products.variant == variant)

        trees = {}
        compat_trees = {}
        for row in query.all():
            id = row.id
            arch = row.arch
            if row.compatlayer:
                if arch not in compat_trees:
                    compat_trees[arch] = id
            else:
                if arch not in trees:
                    trees[arch] = id
        return list(trees.values()) + list(compat_trees.values())

    precalc_treelist = staticmethod(precalc_treelist)

    def dest_get_archs(
        trees, src_arch, names, cache_entry, version=None, overrides=None
    ):
        """Return a list of arches that this package/arch combination ships on."""

        if trees is None:
            return {name: src_arch for name in names}

        query = (
            models.Trees.query.with_entities(
                models.Trees.arch, models.Packages.name
            )
            .join(models.Trees.packages)
            .filter(
                models.Packages.arch == src_arch,
                models.Packages.name.in_(names),
                models.Trees.id.in_(trees),
                models.Trees.imported == 1,
            )
        )
        if version:
            query = query.filter(models.Packages.version == version)

        ret = {}
        for arow in query.all():
            ret.setdefault(arow.name, {}).setdefault(arow.arch, 1)

        for name in names:
            # use cached map entry if there are no records from treetables
            if koji.is_debuginfo(name) and not ret.get(name, {}):
                ret[name] = copy.deepcopy(cache_entry)

            if (
                overrides
                and name in overrides
                and src_arch in overrides[name]
                and not version
            ):
                for tree_arch, include in overrides[name][src_arch].items():
                    if include:
                        ret.setdefault(name, {}).setdefault(tree_arch, 1)
                    elif name in ret and tree_arch in ret[name]:
                        del ret[name][tree_arch]
        return ret

    dest_get_archs = staticmethod(dest_get_archs)

    def get_module_overrides(
        product, version, module_name, module_stream, variant=None
    ):
        """Returns the list of module overrides for the particular product specified."""

        query = models.ModuleOverrides.query.join(
            models.ModuleOverrides.productref
        ).filter(
            models.Products.label == product,
            models.Products.version == version,
            models.ModuleOverrides.name == module_name,
            models.ModuleOverrides.stream == module_stream,
        )
        if variant:
            query = query.filter(models.Products.variant == variant)

        return [row.product_arch for row in query.all()]

    get_module_overrides = staticmethod(get_module_overrides)

    @staticmethod
    def get_product_labels():
        rows = (
            models.Products.query.with_entities(models.Products.label)
            .distinct()
            .all()
        )
        return [{"label": row.label} for row in rows]


def getProductInfo(label):
    """
    Get a list of the versions and variants of a product with the given label.
    """
    return Products.get_product_info(label)


def getProductLabels():
    return Products.get_product_labels()


def getProductListings(productLabel, buildInfo):
    """
    Get a map of which variants of the given product included packages built
    by the given build, and which arches each variant included.
    """
    session = get_koji_session()
    build = get_build(buildInfo, session)

    rpms = session.listRPMs(buildID=build["id"])
    if not rpms:
        raise ProductListingsNotFoundError(
            "Could not find any RPMs for build: %s" % buildInfo
        )

    # sort rpms, so first part of list consists of sorted 'normal' rpms and
    # second part are sorted debuginfos
    debuginfos = [x for x in rpms if "-debuginfo" in x["nvr"]]
    base_rpms = [x for x in rpms if "-debuginfo" not in x["nvr"]]
    rpms = sorted(base_rpms, key=lambda x: x["nvr"]) + sorted(
        debuginfos, key=lambda x: x["nvr"]
    )
    srpm = "%(package_name)s-%(version)s-%(release)s.src.rpm" % build

    prodinfo = Products.get_product_info(productLabel)
    version, variants = prodinfo

    listings = {}
    match_version = Products.get_match_versions(productLabel)
    for variant in variants:
        if variant is None:
            # dict keys must be a string
            variant = ""
        treelist = Products.precalc_treelist(productLabel, version, variant)
        if not treelist:
            continue
        overrides = Products.get_overrides(productLabel, version, variant)
        cache_map = {}
        for rpm in rpms:
            if rpm["name"] in match_version:
                rpm_version = rpm["version"]
            else:
                rpm_version = None

        # without debuginfos
        rpms_nondebug = [
            rpm for rpm in rpms if not koji.is_debuginfo(rpm["name"])
        ]
        d = {}
        all_archs = {rpm["arch"] for rpm in rpms_nondebug}
        for arch in all_archs:
            d[arch] = Products.dest_get_archs(
                treelist,
                arch,
                [rpm["name"] for rpm in rpms_nondebug if rpm["arch"] == arch],
                cache_map.get(srpm, {}).get(arch, {}),
                rpm_version,
                overrides,
            )

        for rpm in rpms_nondebug:
            dest_archs = d[rpm["arch"]].get(rpm["name"], {}).keys()
            if rpm["arch"] != "src":
                cache_map.setdefault(srpm, {})
                cache_map[srpm].setdefault(rpm["arch"], {})
                for x in dest_archs:
                    cache_map[srpm][rpm["arch"]][x] = 1
            for dest_arch in dest_archs:
                listings.setdefault(variant, {}).setdefault(
                    rpm["nvr"], {}
                ).setdefault(rpm["arch"], []).append(dest_arch)

        # debuginfo only
        rpms_debug = [rpm for rpm in rpms if koji.is_debuginfo(rpm["name"])]
        d = {}
        all_archs = {rpm["arch"] for rpm in rpms_debug}
        for arch in all_archs:
            d[arch] = Products.dest_get_archs(
                treelist,
                arch,
                [rpm["name"] for rpm in rpms_debug if rpm["arch"] == arch],
                cache_map.get(srpm, {}).get(arch, {}),
                rpm_version,
                overrides,
            )

        for rpm in rpms_debug:
            dest_archs = d[rpm["arch"]].get(rpm["name"], {}).keys()
            if rpm["arch"] != "src":
                cache_map.setdefault(srpm, {})
                cache_map[srpm].setdefault(rpm["arch"], {})
                for x in dest_archs:
                    cache_map[srpm][rpm["arch"]][x] = 1
            for dest_arch in dest_archs:
                listings.setdefault(variant, {}).setdefault(
                    rpm["nvr"], {}
                ).setdefault(rpm["arch"], []).append(dest_arch)

        for variant in list(listings.keys()):
            nvrs = list(listings[variant].keys())
            # BREW-260: Read allow_src_only flag for the product/version
            allow_src_only = Products.get_srconly_flag(productLabel, version)
            if len(nvrs) == 1:
                maps = list(listings[variant][nvrs[0]].keys())
                # BREW-260: check for allow_src_only flag added
                if len(maps) == 1 and maps[0] == "src" and not allow_src_only:
                    del listings[variant]
    return listings


def getModuleProductListings(productLabel, moduleNVR):
    """
    Get a map of which variants of the given product included the given module,
    and which arches each variant included.
    """
    build = get_build(moduleNVR)
    try:
        module = build["extra"]["typeinfo"]["module"]
        module_name = module["name"]
        module_stream = module["stream"]
    except (KeyError, TypeError):
        raise ProductListingsNotFoundError(
            "It's not a module build: %s" % moduleNVR
        )

    prodinfo = Products.get_product_info(productLabel)
    version, variants = prodinfo

    listings = {}
    for variant in variants:
        if variant is None:
            # dict keys must be a string
            variant = ""
        trees = Products.precalc_treelist(productLabel, version, variant)

        module_trees = (
            models.Trees.query.with_entities(models.Trees.arch)
            .join(models.Trees.modules)
            .filter(
                models.Modules.name == module_name,
                models.Modules.stream == module_stream,
            )
            .filter(models.Trees.id.in_(trees))
        )

        overrides = Products.get_module_overrides(
            productLabel, version, module_name, module_stream, variant
        )

        archs = sorted(set([arch for arch, in module_trees] + overrides))

        if archs:
            listings.setdefault(variant, archs)

    return listings
