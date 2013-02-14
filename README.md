PyTradeLib
==========

PyTradeLib is a python library for managing instrument data, screening and
backtesting.

### Thanks and Acknowledgements
- Gabriel Martin Becedillas Ruiz, for authoring the original PyAlgoTrade  
- John Benediktsson, for authoring the talib wrapper and helping me extensively  
- The authors of the original TA-Lib, zipline, and the entire SciPy community
  for all of the excellent tools and documentation!  
- And, well, the internet.  

### So what's different?
- The entire API is a more pythonic lower_cased_api.  
- Everything uses new-style classes now.  
- Newly added files are licensed under the LGPLv3+.  
- Symbol Data Management in general got completely rewritten and expanded:  
  - Downloading of data for more than one symbol at a time sees huge performance
    increases.  
  - Added a stock screener that can filter on fundamentals and/or backtest results.  
  - Data is (optionally) kept automatically updated by a daemon running in the
    background, or manually by a convenience script. [PARTIAL - quote server too?]  
  - Memory usage while backtesting with many symbols is significantly decreased
    due primarily to wider use of generators throughout the library. [PARTIAL]  

### TODO:  
- Add timezone support across the board.  
- Python properties should be used in preference over getter/setter functions.  
- Lots of work on StrategyAnalyzers left to do. [results in SQL?]  
- Convert storage of non-historical data to SQL. [MOSTLY DONE, needs testing]  
- Convert testing to nosetests.  
- Convert underlying data structures to numpy arrays for better performance,
  memory usage and integration with talib.  
- Work on improving local multiprocessing optimizer.  
- Then work on improving local network/multi-system multiprocessing optimizer.  

### Regressions:
- The homegrown indicators from PyAlgoTrade have been removed in favor of talib.  
- For the time being, googleappengine support has also been removed.  


Installing
==========

### Dependencies:
[python](http://www.python.org/) 2.7.x  
[numpy](http://www.numpy.org/)  
[matplotlib](http://matplotlib.org/)  
[gevent](http://www.gevent.org/) [TODO: replace with something that supports Windows?]  
[lz4](https://github.com/steeve/python-lz4) [TODO: make optional]  
[decorator](http://pypi.python.org/pypi/decorator)  

### Install PyTradeLib:
```
$ git clone git://github.com/briancappello/PyTradeLib.git  
$ cd PyTradeLib  
$ sudo python setup.py install
```
