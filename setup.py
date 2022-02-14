from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

setup(
    name="ibl-pipeline",
    version="0.9.5",
    description="Datajoint schemas for IBL",
    author="Vathes",
    author_email="support@datajoint.com",
    packages=find_packages(exclude=[]),
    install_requires=[
        "boto3",
        "colorlover",
        "datajoint",
        "ONE-api",
        "plotly",
        "scikits-bootstrap",
        "scipy",
        "seaborn",
        "statsmodels",
    ],
)
