#!/usr/bin/env python

from distutils.core import setup

setup(
    name='PyTradeLab',
    version='0.0.1',
    description='Python Trading Library and Utilities',
    long_description='Python trading library and utilities for symbol data management, screening and backtesting.',
    author='Brian A Cappello',
    author_email='briancappello@gmail.com',
    url='',
    download_url='',
    packages=[
        'pytradelab',
        'pytradelab.barfeed',
        'pytradelab.broker',
        'pytradelab.optimizer',
        'pytradelab.stratanalyzer',
        'pytradelab.talibext',
        'pytradelab.technical',
        'pytradelab.tools',
        'pytradelab.utils',
        ],
)
