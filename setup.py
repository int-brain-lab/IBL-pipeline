from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

setup(
    name="ibl-pipeline",
    version="0.9.5",
    description="DataJoint schemas for IBL",
    author="DataJoint",
    author_email="info@datajoint.com",
    packages=find_packages(include=["ibl_pipeline"]),
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
