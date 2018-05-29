import os
from setuptools import setup, find_packages


readme = os.path.join(os.path.dirname(__file__), 'README.rst')
LONG_DESCRIPTION = open(readme).read()


version = '0.1.0'


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
