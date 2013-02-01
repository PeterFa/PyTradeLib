technical -- Technical indicators
=================================

.. module:: pytradelab.technical
.. autoclass:: pytradelab.technical.DataSeriesFilter
    :members: calculateValue, get_data_series, getWindowSize

Example
-------

Creating a custom filter is easy:

.. literalinclude:: ../samples/technical-1.py

The output should be:

.. literalinclude:: ../samples/technical-1.output

Moving Averages
---------------

.. automodule:: pytradelab.technical.ma
    :members: SMA, EMA, WMA

Momentum Indicators
-------------------

.. automodule:: pytradelab.technical.rsi
    :members: RSI

.. automodule:: pytradelab.technical.stoch
    :members: StochasticOscillator

.. automodule:: pytradelab.technical.roc
    :members: RateOfChange

Other Indicators
----------------

.. automodule:: pytradelab.technical.trend
    :members: Slope

.. automodule:: pytradelab.technical.cross
    :members: CrossAbove, CrossBelow

