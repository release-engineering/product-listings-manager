import os
import re
from setuptools import setup, find_packages


readme = os.path.join(os.path.dirname(__file__), 'README.rst')
LONG_DESCRIPTION = open(readme).read()


def read_module_contents():
    with open('product_listings_manager/__init__.py') as init:
        return init.read()


def read_requirements(filename):
    specifiers = []
    dep_links = []
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('-r') or line.strip() == '':
                continue
            if line.startswith('git+'):
                dep_links.append(line.strip())
            else:
                specifiers.append(line.strip())
    return specifiers, dep_links


setup_py_path = os.path.dirname(os.path.realpath(__file__))
install_requires, _ = read_requirements(os.path.join(setup_py_path, 'requirements.txt'))
tests_requires, _ = read_requirements(os.path.join(setup_py_path, 'test-requirements.txt'))

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
    install_requires=install_requires,
    tests_require=tests_requires
)
