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
        'pytradelab.optimizer',
        'pytradelab.stratanalyzer',
        'pytradelab.talibext',
        'pytradelab.technical',
        'pytradelab.tools',
        'pytradelab.utils',
        ],
)
