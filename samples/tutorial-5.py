from pytradelib import plotter
from pytradelib.barfeed import yahoofeed
from pytradelib.stratanalyzer import returns
import smacross_strategy


# Load the yahoo feed from the CSV file
feed = yahoofeed.Feed()
feed.add_bars_from_csv("orcl", "orcl-2000.csv")

# Evaluate the strategy with the feed's bars.
myStrategy = smacross_strategy.Strategy(feed, 20)

# Attach a returns analyzers to the strategy.
returnsAnalyzer = returns.Returns()
myStrategy.attach_analyzer(returnsAnalyzer)

# Attach the plotter to the strategy.
plt = plotter.StrategyPlotter(myStrategy)
# Include the SMA in the symbol's subplot to get it displayed along with the closing prices.
plt.get_symbolSubplot("orcl").addDataSeries("SMA", myStrategy.getSMA())
# Plot the strategy returns at each bar.
plt.getOrCreateSubplot("returns").addDataSeries("Net return", returnsAnalyzer.get_returns())
plt.getOrCreateSubplot("returns").addDataSeries("Cum. return", returnsAnalyzer.get_cumulative_returns())

# Run the strategy.
myStrategy.run()
print "Final portfolio value: $%.2f" % myStrategy.get_result()

# Plot the strategy.
plt.plot()

