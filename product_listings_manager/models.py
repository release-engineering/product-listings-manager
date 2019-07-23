"""Models definition relecting tables in composedb.

These models are not fully relecting the composedb schema:

- Tables and columns which not needed by PLM are not included.

- Length of db.String() column is not required by postgresql(composedb uses it), in case of
testing with other db backend(e.g. sqlite) a value is given in following definition and it
has no side effect to postgresql(composedb).
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Packages(db.Model):
    """packages table in composedb.

    Only needed columns in packages table are defined here.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    arch = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return '<Package %d %s %s %s>' % (self.id, self.name, self.version, self.arch)


tree_product_map = db.Table(
    'tree_product_map',
    db.Column('tree_id', db.Integer, db.ForeignKey('trees.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True)
)


class Products(db.Model):
    """products table in composedb."""
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    variant = db.Column(db.String(200))
    allow_source_only = db.Column(db.Boolean)
    module_overrides = db.relationship('ModuleOverrides', backref='productref')
    overrides = db.relationship('Overrides', backref='productref')
    trees = db.relationship('Trees', secondary=tree_product_map, backref='products')

    def __repr__(self):
        return '<Product %d %s %s %s %s>' % (self.id, self.label, self.version, self.variant, self.allow_source_only)


tree_packages = db.Table(
    'tree_packages',
    db.Column('trees_id', db.Integer, db.ForeignKey('trees.id'), primary_key=True),
    db.Column('packages_id', db.Integer, db.ForeignKey('packages.id'), primary_key=True)
)


tree_modules = db.Table(
    'tree_modules',
    db.Column('trees_id', db.Integer, db.ForeignKey('trees.id'), primary_key=True),
    db.Column('modules_id', db.Integer, db.ForeignKey('modules.id'), primary_key=True)
)


class Trees(db.Model):
    """trees table in composedb."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    buildname = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    arch = db.Column(db.String(10), nullable=False)
    treetype = db.Column(db.String(255))
    treeinfo = db.Column(db.String(255))
    imported = db.Column(db.Integer, nullable=False)
    product = db.Column(db.Integer)
    compatlayer = db.Column(db.Boolean, nullable=False)
    packages = db.relationship('Packages', secondary=tree_packages)
    modules = db.relationship('Modules', secondary=tree_modules)

    def __repr__(self):
        return '<Tree %d %s %s %s>' % (self.id, self.name, self.date, self.arch)


class Overrides(db.Model):
    """overrides table in composedb.

    Many columns are set as primary key becasue primary key is required
    in SQLAlchemy ORM and these columns are unique together.

    https://docs.sqlalchemy.org/en/latest/faq/ormconfiguration.html#how-do-i-map-a-table-that-has-no-primary-key
    """
    name = db.Column(db.String(255), primary_key=True)
    pkg_arch = db.Column(db.String(32), primary_key=True)
    product_arch = db.Column(db.String(32), primary_key=True)
    product = db.Column(db.Integer, db.ForeignKey('products.id'), primary_key=True)
    include = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return '<Overrides %s %s %s %s %s>' % (self.name, self.pkg_arch, self.product_arch, self.product, self.include)


class MatchVersions(db.Model):
    """match_versions table in composedb."""
    name = db.Column(db.String(255), primary_key=True)
    product = db.Column(db.String(100), primary_key=True)

    def __repr__(self):
        return '<MatchVersion %s %s>' % (self.id, self.name, self.product)


class Modules(db.Model):
    """modules table in composedb."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    stream = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return '<Module %d %s %s %s>' % (self.id, self.name, self.stream, self.version)


class ModuleOverrides(db.Model):
    """module_overrides table in composedb."""
    name = db.Column(db.String(255), primary_key=True)
    stream = db.Column(db.String(255), primary_key=True)
    product = db.Column(db.Integer, db.ForeignKey('products.id'), primary_key=True)
    product_arch = db.Column(db.String(32), primary_key=True)

    def __repr__(self):
        return '<ModuleOverrides %s %s %d %s>' % (self.name, self.stream, self.product, self.product_arch)
