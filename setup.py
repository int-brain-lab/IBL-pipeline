#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='alyx-pipeline',
    version='0.0.0',
    description='Datajoint schemas for IBL',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint'],
)
