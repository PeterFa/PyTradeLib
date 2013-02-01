stratanalyzer -- Strategy analyzers
===================================

Strategy analyzers provide an extensible way to attach different calculations to strategy executions.

.. automodule:: pytradelab.stratanalyzer
    :members: StrategyAnalyzer

Returns
-------
.. automodule:: pytradelab.stratanalyzer.returns
    :members: Returns

Sharpe Ratio
------------
.. automodule:: pytradelab.stratanalyzer.sharpe
    :members: SharpeRatio

DrawDown
--------
.. automodule:: pytradelab.stratanalyzer.drawdown
    :members: DrawDown

Trades
------
.. automodule:: pytradelab.stratanalyzer.trades
    :members: Trades
    :member-order: bysource

Example
-------
This example depends on smacross_strategy.py from the tutorial section.

.. literalinclude:: ../samples/sample-strategy-analyzer.py

The output should look like this:

.. literalinclude:: ../samples/sample-strategy-analyzer.output
