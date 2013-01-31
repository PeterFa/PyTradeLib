technical -- Technical indicators
=================================

.. module:: pyalgotrade.technical
.. autoclass:: pyalgotrade.technical.DataSeriesFilter
    :members: calculateValue, get_data_series, getWindowSize

Example
-------

Creating a custom filter is easy:

.. literalinclude:: ../samples/technical-1.py

The output should be:

.. literalinclude:: ../samples/technical-1.output

Moving Averages
---------------

.. automodule:: pyalgotrade.technical.ma
    :members: SMA, EMA, WMA

Momentum Indicators
-------------------

.. automodule:: pyalgotrade.technical.rsi
    :members: RSI

.. automodule:: pyalgotrade.technical.stoch
    :members: StochasticOscillator

.. automodule:: pyalgotrade.technical.roc
    :members: RateOfChange

Other Indicators
----------------

.. automodule:: pyalgotrade.technical.trend
    :members: Slope

.. automodule:: pyalgotrade.technical.cross
    :members: CrossAbove, CrossBelow

