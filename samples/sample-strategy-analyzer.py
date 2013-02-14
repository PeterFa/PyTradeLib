from pytradelib.barfeed import yahoofeed
from pytradelib.stratanalyzer import returns
from pytradelib.stratanalyzer import sharpe
from pytradelib.stratanalyzer import drawdown
from pytradelib.stratanalyzer import trades
import smacross_strategy

# Load the yahoo feed from the CSV file
feed = yahoofeed.Feed()
feed.add_bars_from_csv("orcl", "orcl-2000.csv")

# Evaluate the strategy with the feed's bars.
myStrategy = smacross_strategy.Strategy(feed, 20)

# Attach different analyzers to a strategy before executing it.
retAnalyzer = returns.Returns()
myStrategy.attach_analyzer(retAnalyzer)
sharpeRatioAnalyzer = sharpe.SharpeRatio()
myStrategy.attach_analyzer(sharpeRatioAnalyzer)
drawDownAnalyzer = drawdown.DrawDown()
myStrategy.attach_analyzer(drawDownAnalyzer)
tradesAnalyzer = trades.Trades()
myStrategy.attach_analyzer(tradesAnalyzer)

# Run the strategy.
myStrategy.run()

print "Final portfolio value: $%.2f" % myStrategy.get_result()
print "Cumulative returns: %.2f %%" % (retAnalyzer.get_cumulative_returns()[-1] * 100)
print "Sharpe ratio: %.2f" % (sharpeRatioAnalyzer.get_sharpe_ratio(0.05, 252))
print "Max. drawdown: %.2f %%" % (drawDownAnalyzer.get_max_draw_down() * 100)
print "Longest drawdown duration: %d days" % (drawDownAnalyzer.get_longest_draw_down_duration())

print
print "Total trades: %d" % (tradesAnalyzer.get_count())
if tradesAnalyzer.get_count() > 0:
    profits = tradesAnalyzer.get_all()
    print "Avg. profit: $%2.f" % (profits.mean())
    print "Profits std. dev.: $%2.f" % (profits.std())
    print "Max. profit: $%2.f" % (profits.max())
    print "Min. profit: $%2.f" % (profits.min())
    returns = tradesAnalyzer.get_all_returns()
    print "Avg. return: %2.f %%" % (returns.mean() * 100)
    print "Returns std. dev.: %2.f %%" % (returns.std() * 100)
    print "Max. return: %2.f %%" % (returns.max() * 100)
    print "Min. return: %2.f %%" % (returns.min() * 100)

print
print "Profitable trades: %d" % (tradesAnalyzer.get_profitable_count())
if tradesAnalyzer.get_profitable_count() > 0:
    profits = tradesAnalyzer.get_profits()
    print "Avg. profit: $%2.f" % (profits.mean())
    print "Profits std. dev.: $%2.f" % (profits.std())
    print "Max. profit: $%2.f" % (profits.max())
    print "Min. profit: $%2.f" % (profits.min())
    returns = tradesAnalyzer.get_positive_returns()
    print "Avg. return: %2.f %%" % (returns.mean() * 100)
    print "Returns std. dev.: %2.f %%" % (returns.std() * 100)
    print "Max. return: %2.f %%" % (returns.max() * 100)
    print "Min. return: %2.f %%" % (returns.min() * 100)

print
print "Unprofitable trades: %d" % (tradesAnalyzer.get_unprofitable_count())
if tradesAnalyzer.get_unprofitable_count() > 0:
    losses = tradesAnalyzer.get_losses()
    print "Avg. loss: $%2.f" % (losses.mean())
    print "Losses std. dev.: $%2.f" % (losses.std())
    print "Max. loss: $%2.f" % (losses.min())
    print "Min. loss: $%2.f" % (losses.max())
    returns = tradesAnalyzer.get_negative_returns()
    print "Avg. return: %2.f %%" % (returns.mean() * 100)
    print "Returns std. dev.: %2.f %%" % (returns.std() * 100)
    print "Max. return: %2.f %%" % (returns.max() * 100)
    print "Min. return: %2.f %%" % (returns.min() * 100)

