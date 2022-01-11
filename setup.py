#!/usr/bin/env python
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

setup(
    name="ibl-pipeline",
    version="0.9.1",
    description="Datajoint schemas for IBL",
    author="Vathes",
    author_email="support@vathes.com",
    packages=find_packages(exclude=[]),
    install_requires=[
        "datajoint==0.12.9",
        "ibllib",
        "numpy>=1.18.1",
        "seaborn>=0.10.0",
        "globus_sdk",
        "boto3",
        "colorlover",
        "scikits.bootstrap",
        "statsmodels",
        "plotly",
    ],
    scripts=["scripts/ibl-shell.py"],
)
