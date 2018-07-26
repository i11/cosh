# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as f:
  readme = f.read()

with open('LICENSE') as f:
  license = f.read()

setup(
  name='cosh',
  version='0.1.0',
  description='Container Shell',
  long_description=readme,
  author='Ilja Bobkevic',
  author_email='ilja@bobkevic.com',
  url='https://github.com/i11/cosh',
  license=license,
  packages=find_packages(exclude=('tests', 'docs')),
  scripts=[
    'bin/cosh'
  ],
  install_requires=[
    'docker==3.4.1',
    'argparse==1.4.0',
    'requests==2.19.1'
  ]
)
