#!/usr/bin/env python3
"""
Setup configuration for the WHOOP Data package
"""

from setuptools import setup, find_packages
import os
import sys

# Add project root to path to import version
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from whoopdata.__version__ import __version__

# Read requirements from requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read README for long description
try:
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "WHOOP and Withings Health Data Integration Platform"

setup(
    name="whoop-data",
    version=__version__,
    description="WHOOP and Withings Health Data Integration Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/whoop-data",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ]
    },
    entry_points={
        "console_scripts": [
            "whoop-start=whoopdata.cli:main",
            "whoop-etl=whoopdata.etl:run_complete_etl",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
    keywords="health data whoop withings api fastapi",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/whoop-data/issues",
        "Source": "https://github.com/yourusername/whoop-data",
    },
)
