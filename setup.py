# This file is part of PyTradeLab.
#
# Copyright 2013 Brian A Cappello <briancappello at gmail>
#
# PyTradeLab is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyTradeLab is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyTradeLab.  If not, see http://www.gnu.org/licenses/

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
    classifiers = [
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Financial and Insurance Industry",
        ],
    packages=[
        'pytradelab',
        'pytradelab.barfeed',
        'pytradelab.broker',
        'pytradelab.dataproviders',
        'pytradelab.dataproviders.yahoo',
        'pytradelab.deprecated',
        'pytradelab.optimizer',
        'pytradelab.stratanalyzer',
        'pytradelab.technical',
        'pytradelab.utils',
        ],
)
