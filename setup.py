#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TODO:
    look into pbr for versioning?
"""
from setuptools import setup
import sys
from os.path import exists


def parse_version(fpath):
    """
    Statically parse the version number from a python file
    """
    import ast
    if not exists(fpath):
        raise ValueError('fpath={!r} does not exist'.format(fpath))
    with open(fpath, 'r') as file_:
        sourcecode = file_.read()
    pt = ast.parse(sourcecode)
    class VersionVisitor(ast.NodeVisitor):
        def visit_Assign(self, node):
            for target in node.targets:
                if getattr(target, 'id', None) == '__version__':
                    self.version = node.value.s
    visitor = VersionVisitor()
    visitor.visit(pt)
    return visitor.version


def parse_requirements(fname='requirements.txt', with_version=False):
    """
    Parse the package dependencies listed in a requirements file but strips
    specific versioning information.

    Args:
        fname (str): path to requirements file
        with_version (bool, default=False): if true include version specs

    Returns:
        List[str]: list of requirements items
    """
    from os.path import exists, dirname, join
    import re
    require_fpath = fname

    def parse_line(line, dpath=''):
        """
        Parse information from a line in a requirements text file

        line = 'git+https://a.com/somedep@sometag#egg=SomeDep'
        line = '-e git+https://a.com/somedep@sometag#egg=SomeDep'
        """
        # Remove inline comments
        comment_pos = line.find(' #')
        if comment_pos > -1:
            line = line[:comment_pos]

        if line.startswith('-r '):
            # Allow specifying requirements in other files
            target = join(dpath, line.split(' ')[1])
            for info in parse_require_file(target):
                yield info
        else:
            # See: https://www.python.org/dev/peps/pep-0508/
            info = {'line': line}
            if line.startswith('-e '):
                info['package'] = line.split('#egg=')[1]
            else:
                if ';' in line:
                    pkgpart, platpart = line.split(';')
                    # Handle platform specific dependencies
                    # setuptools.readthedocs.io/en/latest/setuptools.html
                    # #declaring-platform-specific-dependencies
                    plat_deps = platpart.strip()
                    info['platform_deps'] = plat_deps
                else:
                    pkgpart = line
                    platpart = None

                # Remove versioning from the package
                pat = '(' + '|'.join(['>=', '==', '>']) + ')'
                parts = re.split(pat, pkgpart, maxsplit=1)
                parts = [p.strip() for p in parts]

                info['package'] = parts[0]
                if len(parts) > 1:
                    op, rest = parts[1:]
                    version = rest  # NOQA
                    info['version'] = (op, version)
            yield info

    def parse_require_file(fpath):
        dpath = dirname(fpath)
        with open(fpath, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    for info in parse_line(line, dpath=dpath):
                        yield info

    def gen_packages_items():
        if exists(require_fpath):
            for info in parse_require_file(require_fpath):
                parts = [info['package']]
                if with_version and 'version' in info:
                    parts.extend(info['version'])
                if not sys.version.startswith('3.4'):
                    # apparently package_deps are broken in 3.4
                    plat_deps = info.get('platform_deps')
                    if plat_deps is not None:
                        parts.append(';' + plat_deps)
                item = ''.join(parts)
                yield item

    packages = list(gen_packages_items())
    return packages


def parse_description():
    """
    Parse the description in the README file

    CommandLine:
        pandoc --from=markdown --to=rst --output=README.rst README.md
        python -c "import setup; print(setup.parse_description())"
    """
    from os.path import dirname, join, exists
    readme_fpath = join(dirname(__file__), 'README.rst')
    # This breaks on pip install, so check that it exists.
    if exists(readme_fpath):
        with open(readme_fpath, 'r') as f:
            text = f.read()
        return text
    return ''


def native_mb_python_tag(plat_impl=None, version_info=None):
    """
    Get the correct manylinux python version tag for this interpreter

    Example:
        >>> print(native_mb_python_tag())
        >>> print(native_mb_python_tag('PyPy', (2, 7)))
        >>> print(native_mb_python_tag('CPython', (3, 8)))
    """
    if plat_impl is None:
        import platform
        plat_impl = platform.python_implementation()

    if version_info is None:
        import sys
        version_info = sys.version_info

    major, minor = version_info[0:2]
    major, minor = version_info[0:2]
    if minor > 9:
        ver = '{}_{}'.format(major, minor)
    else:
        ver = '{}{}'.format(major, minor)

    if plat_impl == 'CPython':
        # TODO: get if cp27m or cp27mu
        impl = 'cp'
        if ver == '27':
            IS_27_BUILT_WITH_UNICODE = True  # how to determine this?
            if IS_27_BUILT_WITH_UNICODE:
                abi = 'mu'
            else:
                abi = 'm'
        else:
            import sys
            if sys.version_info[:2] >= (3, 8):
                # bpo-36707: 3.8 dropped the m flag
                abi = ''
            else:
                abi = 'm'
        mb_tag = '{impl}{ver}-{impl}{ver}{abi}'.format(**locals())
    elif plat_impl == 'PyPy':
        abi = ''
        impl = 'pypy'
        ver = '{}{}'.format(major, minor)
        mb_tag = '{impl}-{ver}'.format(**locals())
    else:
        raise NotImplementedError(plat_impl)
    return mb_tag


NAME = 'xdoctest'
try:
    VERSION = parse_version('xdoctest/__init__.py')
except Exception:
    raise
    print('failed to parse values in setup.py')
    VERSION = '???'

try:
    MB_PYTHON_TAG = native_mb_python_tag()
except Exception:
    # raise
    MB_PYTHON_TAG = '???'


from setuptools import find_packages  # NOQA
setupkw = dict(
    name=NAME,
    version=VERSION,
    author='Jon Crall',
    author_email='erotemic@gmail.com',
    url='https://github.com/Erotemic/xdoctest',
    license='Apache 2',
)


if __name__ == '__main__':
    setupkw.update(dict(
        description='A rewrite of the builtin doctest module',
        install_requires=parse_requirements('requirements/runtime.txt'),
        extras_require={
            'all': parse_requirements('requirements.txt'),
            'tests': parse_requirements('requirements/tests.txt'),
            'optional': parse_requirements('requirements/optional.txt'),
            'colors': parse_requirements('requirements/colors.txt'),
            'jupyter': parse_requirements('requirements/jupyter.txt'),
        },
        long_description=parse_description(),
        long_description_content_type='text/x-rst',
        entry_points={
            # the pytest11 entry point makes the plugin available to pytest
            'pytest11': [
                'xdoctest = xdoctest.plugin',
            ],
            # the console_scripts entry point creates the xdoctest executable
            'console_scripts': [
                'xdoctest = xdoctest.__main__:main'
            ]
        },
        packages=find_packages('.'),
        # packages=['xdoctest', 'xdoctest.utils', 'xdoctest.docstr'],
        # custom PyPI classifier for pytest plugins
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Utilities',
            'Topic :: Software Development :: Testing',
            'Framework :: Pytest',
            # This should be interpreted as Apache License v2.0
            'License :: OSI Approved :: Apache Software License',
            # Supported Python versions
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python :: Implementation :: CPython',
        ],
    ))
    if sys.version_info[0] == 3 and sys.version_info[1] <= 4:
        setupkw.pop('long_description_content_type', None)
    setup(**setupkw)
