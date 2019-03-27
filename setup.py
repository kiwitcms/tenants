# pylint: disable=missing-docstring

from setuptools import setup, find_packages


def get_long_description():
    with open('README.rst', 'r') as file:
        return file.read()


def get_install_requires(path):
    requires = []
    links = []

    with open(path, 'r') as file:
        for line in file:
            if line.startswith('-r '):
                continue
            requires.append(line.strip())
        return requires


setup(
    name='kiwitcms-tenants',
    version='0.1',
    description='Multi-tenant support for Kiwi TCMS',
    long_description=get_long_description(),
    author='Kiwi TCMS',
    author_email='info@kiwitcms.org',
    url='https://github.com/kiwitcms/tenants/',
    license='GPLv3+',
    install_requires=get_install_requires('requirements.txt'),
    packages=['tcms.tenants'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: Internet',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
