import re
import os
from setuptools import setup, find_packages


readme = os.path.join(os.path.dirname(__file__), 'README.rst')
LONG_DESCRIPTION = open(readme).read()


def read_module_contents():
    with open('product_listings_manager/__init__.py') as init:
        return init.read()


module_file = read_module_contents()
metadata = dict(re.findall("__([a-z]+)__\s*=\s*'([^']+)'", module_file))
version = metadata['version']


setup(name="product-listings-manager",
      version=version,
      description='query product listings data in composedb',
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: MIT License',
                   'Intended Audience :: Developers',
                   'Operating System :: POSIX',
                   'Programming Language :: Python',
                   'Topic :: Software Development',
                   ],
      keywords='product compose',
      author='Ken Dreyer',
      author_email='kdreyer@redhat.com',
      url='https://github.com/ktdreyer/product-listings-manager',
      license='MIT',
      long_description=LONG_DESCRIPTION,
      packages=find_packages(),
      install_requires=[
        'Flask',
        'Flask-XML-RPC',
        'Flask-Restful',
        'koji',
        'pygresql',
      ],
      tests_require=[
          'pytest',
          'mock',
      ],
)
