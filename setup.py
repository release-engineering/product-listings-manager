import re
import os
from setuptools import setup, find_packages


readme = os.path.join(os.path.dirname(__file__), 'README.rst')
LONG_DESCRIPTION = open(readme).read()


def read_module_contents():
    with open('product_listings_manager/__init__.py') as init:
        return init.read()


module_file = read_module_contents()
metadata = dict(re.findall(r"__([a-z]+)__\s*=\s*'([^']+)'", module_file))
version = metadata['version']


setup(
    name="product-listings-manager",
    version=version,
    description='query product listings data in composedb',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development',
    ],
    keywords='product compose',
    author='Ken Dreyer',
    author_email='kdreyer@redhat.com',
    url='https://github.com/release-engineering/product-listings-manager',
    license='MIT',
    long_description=LONG_DESCRIPTION,
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'Flask',
        'Flask-Restful',
        'Flask-SQLAlchemy',
        'SQLAlchemy',
        'koji',
        'psycopg2-binary',
    ],
    tests_require=[
        'pytest',
        'pytest-cov',
        'mock',
        'factory-boy'
    ],
)
