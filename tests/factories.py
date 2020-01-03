import datetime
import factory
from factory.fuzzy import FuzzyNaiveDateTime
from factory.fuzzy import FuzzyText

from product_listings_manager.models import db
from product_listings_manager.models import Packages
from product_listings_manager.models import Products
from product_listings_manager.models import Trees
from product_listings_manager.models import Modules


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = db.session


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

    label = factory.Sequence(lambda n: u"Label-%d" % n)
    version = factory.Sequence(lambda n: u"V%d" % n)
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
