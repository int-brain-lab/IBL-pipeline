#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='ibl_pipeline',
    version='0.0.dev',
    description='Datajoint schemas for IBL',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint>=0.12.dev3'],
    scripts=['scripts/ibl-shell.py'],
)
