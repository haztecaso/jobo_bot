#!/bin/env python3

import setuptools

with open("readme.md", "r") as readme_file:
    long_description = readme_file.read()

setuptools.setup(
    name="jobo_bot",
    version="1.2.0",
    author="Adrián Lattes",
    author_email="adrianlattes@disroot.org",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haztecaso/jobo_bot",
    packages=setuptools.find_packages(),
    scripts = [ "jobo_bot" ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    ],
    python_requires='>=3.6',
)

