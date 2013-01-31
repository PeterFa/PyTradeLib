from pyalgotrade import strategy
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross

class Strategy(strategy.Strategy):
    def __init__(self, feed, smaPeriod):
        strategy.Strategy.__init__(self, feed, 1000)
        closeDS = feed["orcl"].get_close_data_series()
        self.__sma = ma.SMA(closeDS, smaPeriod)
        self.__crossAbove = cross.CrossAbove(closeDS, self.__sma)
        self.__crossBelow = cross.CrossBelow(closeDS, self.__sma)
        self.__position = None

    def getSMA(self):
        return self.__sma

    def on_enter_canceled(self, position):
        self.__position = None

    def on_exit_ok(self, position):
        self.__position = None

    def on_exit_canceled(self, position):
        # If the exit was canceled, re-submit it.
        self.exit_position(self.__position)

    def on_bars(self, bars):
        # Wait for enough bars to be available to calculate the CrossAbove indicator.
        if self.__crossAbove is None:
            return

        # If a position was not opened, check if we should enter a long position.
        if self.__position == None:
            if self.__crossAbove.get_value() > 0:
                # Enter a buy market order for 10 orcl shares. The order is good till canceled.
                self.__position = self.enter_long("orcl", 10, True)
        # Check if we have to exit the position.
        elif self.__crossBelow.get_value() > 0:
            self.exit_position(self.__position)

