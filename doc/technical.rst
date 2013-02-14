technical -- Technical indicators
=================================

.. module:: pytradelib.technical
.. autoclass:: pytradelib.technical.DataSeriesFilter
    :members: calculateValue, get_data_series, getWindowSize

Example
-------

Creating a custom filter is easy:

.. literalinclude:: ../samples/technical-1.py

The output should be:

.. literalinclude:: ../samples/technical-1.output

Moving Averages
---------------

.. automodule:: pytradelib.technical.ma
    :members: SMA, EMA, WMA

Momentum Indicators
-------------------

.. automodule:: pytradelib.technical.rsi
    :members: RSI

.. automodule:: pytradelib.technical.stoch
    :members: StochasticOscillator

.. automodule:: pytradelib.technical.roc
    :members: RateOfChange

Other Indicators
----------------

.. automodule:: pytradelib.technical.trend
    :members: Slope

.. automodule:: pytradelib.technical.cross
    :members: CrossAbove, CrossBelow

