#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='ibl_pipeline',
    version='0.2.2',
    description='Datajoint schemas for IBL',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint>=0.12', 'ibllib>=1.4.11', 'numpy>=1.18.1', 'seaborn>=0.10.0', 'globus_sdk', 'boto3', 'colorlover', 'scikits.bootstrap', 'statsmodels>=0.10.1', 'plotly>=4.1.0'],
    scripts=['scripts/ibl-shell.py'],
)
