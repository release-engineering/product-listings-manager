import datetime

import factory
from factory.fuzzy import FuzzyNaiveDateTime, FuzzyText

from product_listings_manager.models import (
    BaseModel,
    Modules,
    Packages,
    Products,
    SessionLocal,
    Trees,
    engine,
)

BaseModel.metadata.create_all(bind=engine)


class BaseFactoryWithID(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = SessionLocal()
        sqlalchemy_session_persistence = "commit"

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

    label = factory.Sequence(lambda n: "Label-%d" % n)
    version = factory.Sequence(lambda n: "V%d" % n)
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
