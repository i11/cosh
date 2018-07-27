# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as f:
  readme = f.read()

with open('LICENSE') as f:
  license = f.read()

version_format = '{tag}'
url='https://github.com/i11/cosh',

setup(
  name='cosh',
  version_format=version_format,
  description='Container Shell',
  long_description=readme,
  author='Ilja Bobkevic',
  author_email='ilja@bobkevic.com',
  url=url,
  license=license,
  packages=find_packages(exclude=('tests', 'docs')),
  scripts=[
    'bin/cosh'
  ],
  setup_requires=[
    'setuptools-git-version==1.0.3'
  ],
  install_requires=[
    'docker==3.4.1',
    'argparse==1.4.0',
    'requests==2.19.1'
  ],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Natural Language :: English',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3.6',
  ]
)
