"""Models definition relecting tables in composedb.

These models are not fully relecting the composedb schema:

- Tables and columns which not needed by PLM are not included.

- Length of String() column is not required by postgresql(composedb uses
  it), in case of testing with other db backend(e.g. sqlite) a value is given
  in following definition and it has no side effect to postgresql(composedb).
"""
import os

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite://")

if DATABASE_URL.startswith("sqlite://"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class BaseModel(DeclarativeBase):
    pass


if os.getenv("PLM_INIT_DB") == "1":
    BaseModel.metadata.create_all(bind=engine)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Packages(BaseModel):
    """packages table in composedb.

    Only needed columns in packages table are defined here.
    """

    __tablename__ = "packages"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    arch = Column(String(32), nullable=False)
    version = Column(String(255), nullable=False)

    def __repr__(self):
        return "<Package %d %s %s %s>" % (
            self.id,
            self.name,
            self.version,
            self.arch,
        )


class TreeProductMap(BaseModel):
    __tablename__ = "tree_product_map"

    tree_id = Column(Integer, ForeignKey("trees.id"), primary_key=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        primary_key=True,
    )


class Products(BaseModel):
    """products table in composedb."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    label = Column(String(100), nullable=False)
    version = Column(String(100), nullable=False)
    variant = Column(String(200))
    allow_source_only = Column(Boolean)
    module_overrides = relationship("ModuleOverrides", backref="productref")
    overrides = relationship("Overrides", backref="productref")
    trees = relationship(
        "Trees", secondary="tree_product_map", backref="products"
    )

    def __repr__(self):
        return "<Product %d %s %s %s %s>" % (
            self.id,
            self.label,
            self.version,
            self.variant,
            self.allow_source_only,
        )


class TreePackages(BaseModel):
    __tablename__ = "tree_packages"

    trees_id = Column(Integer, ForeignKey("trees.id"), primary_key=True)
    packages_id = Column(
        Integer,
        ForeignKey("packages.id"),
        primary_key=True,
    )


class TreeModules(BaseModel):
    __tablename__ = "tree_modules"

    trees_id = Column(Integer, ForeignKey("trees.id"), primary_key=True)
    modules_id = Column(Integer, ForeignKey("modules.id"), primary_key=True)


class Trees(BaseModel):
    """trees table in composedb."""

    __tablename__ = "trees"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    buildname = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    arch = Column(String(10), nullable=False)
    treetype = Column(String(255))
    treeinfo = Column(String(255))
    imported = Column(Integer, nullable=False)
    product = Column(Integer)
    compatlayer = Column(Boolean, nullable=False)
    packages = relationship("Packages", secondary="tree_packages")
    modules = relationship("Modules", secondary="tree_modules")

    def __repr__(self):
        return "<Tree %d %s %s %s>" % (
            self.id,
            self.name,
            self.date,
            self.arch,
        )


class Overrides(BaseModel):
    """overrides table in composedb.

    Many columns are set as primary key becasue primary key is required
    in SQLAlchemy ORM and these columns are unique together.

    https://docs.sqlalchemy.org/en/latest/faq/ormconfiguration.html#how-do-i-map-a-table-that-has-no-primary-key
    """

    __tablename__ = "overrides"

    name = Column(String(255), primary_key=True)
    pkg_arch = Column(String(32), primary_key=True)
    product_arch = Column(String(32), primary_key=True)
    product = Column(Integer, ForeignKey("products.id"), primary_key=True)
    include = Column(Boolean, nullable=False)

    def __repr__(self):
        return "<Overrides {} {} {} {} {}>".format(
            self.name,
            self.pkg_arch,
            self.product_arch,
            self.product,
            self.include,
        )


class MatchVersions(BaseModel):
    """match_versions table in composedb."""

    __tablename__ = "match_versions"

    name = Column(String(255), primary_key=True)
    product = Column(String(100), primary_key=True)

    def __repr__(self):
        return "<MatchVersion {} {} {}>".format(
            self.id, self.name, self.product
        )


class Modules(BaseModel):
    """modules table in composedb."""

    __tablename__ = "modules"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    stream = Column(String(255), nullable=False)
    version = Column(String(255), nullable=False)

    def __repr__(self):
        return "<Module %d %s %s %s>" % (
            self.id,
            self.name,
            self.stream,
            self.version,
        )


class ModuleOverrides(BaseModel):
    """module_overrides table in composedb."""

    __tablename__ = "module_overrides"

    name = Column(String(255), primary_key=True)
    stream = Column(String(255), primary_key=True)
    product = Column(Integer, ForeignKey("products.id"), primary_key=True)
    product_arch = Column(String(32), primary_key=True)

    def __repr__(self):
        return "<ModuleOverrides %s %s %d %s>" % (
            self.name,
            self.stream,
            self.product,
            self.product_arch,
        )
