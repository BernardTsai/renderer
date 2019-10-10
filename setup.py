#!/usr/bin/env python3

from distutils.core import setup

setup(
    name         = 'render',
    version      = '0.0.0',
    description  = 'A script to render yaml with the help of jinja2 templates',
    author       = 'Bernard Tsai',
    author_email = 'bernard@tsai.eu',
    url          = 'https://github.com/BernardTsai/renderer',
    py_modules   = ['render'],
    install_requires=[
        "Jinja2",
        "PyYAML",
    ],
)
