import datetime

import factory
from factory.fuzzy import FuzzyNaiveDateTime, FuzzyText

from product_listings_manager.models import (
    BaseModel,
    Modules,
    Overrides,
    Packages,
    Products,
    SessionLocal,
    Trees,
    engine,
)

BaseModel.metadata.create_all(bind=engine)


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = SessionLocal()
        sqlalchemy_session_persistence = "commit"


class BaseFactoryWithID(BaseFactory):
    id = factory.Sequence(lambda n: n)


class PackagesFactory(BaseFactoryWithID):
    class Meta:
        model = Packages

    name = FuzzyText()
    arch = FuzzyText()
    version = FuzzyText()


class ProductsFactory(BaseFactoryWithID):
    class Meta:
        model = Products

    label = factory.Sequence(lambda n: f"Label-{n}")
    version = factory.Sequence(lambda n: f"V{n}")
    variant = FuzzyText()
    allow_source_only = False


class TreesFactory(BaseFactoryWithID):
    class Meta:
        model = Trees

    name = FuzzyText()
    buildname = FuzzyText()
    date = FuzzyNaiveDateTime(datetime.datetime.now())
    arch = FuzzyText()
    imported = 1
    compatlayer = False


class ModulesFactory(BaseFactoryWithID):
    class Meta:
        model = Modules

    name = FuzzyText()
    stream = FuzzyText()
    version = FuzzyText()


class OverridesFactory(BaseFactory):
    class Meta:
        model = Overrides

    name = FuzzyText()
    pkg_arch = FuzzyText()
    product_arch = FuzzyText()
    product = None
    include = False
