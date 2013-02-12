from pytradelab import bar
from pytradelab import barfeed
from pytradelab import historicalmanager


class Feed(barfeed.BarFeed):
    def __init__(self, frequency=None, bar_filter=None):
        frequency = frequency or bar.Frequency.DAY
        barfeed.BarFeed.__init__(self, frequency)
        self._historical_reader = historicalmanager.DataManager()
        self._bar_filter = bar_filter
        self._instruments = {}

    def get_symbols(self):
        return self._instruments.keys()

    def get_instruments(self):
        return self._instruments

    def set_bar_filter(self, bar_filter):
        self._bar_filter = bar_filter

    def add_bars_from_symbol(self, symbol):
        self.add_bars_from_symbols([symbol])

    def add_bars_from_symbols(self, symbols):
        self._historical_reader.set_bar_filter(self._bar_filter)
        symbol_bars = self._historical_reader.get_bars_dict(symbols)
        for symbol, bars in symbol_bars.items():
            self.add_bars_from_sequence(symbol, bars)

    def add_bars_from_instrument(self, instrument):
        self._instruments[instrument.symbol()] = instrument
        self.add_bars_from_symbol(instrument.symbol())

    def add_bars_from_instruments(self, instruments):
        for instrument in instruments:
            self._instruments[instrument.symbol()] = instrument
        self.add_bars_from_symbols([x.symbol() for x in instruments])

    #def add_bars_from_instruments(self, instruments):
        #self.tasks = multiprocessing.JoinableQueue()
        #self.results = multiprocessing.Queue()

        ## start workers
        #num_workers = multiprocessing.cpu_count() + 1
        #workers = [CSVWorker(self.tasks, self.results) for i in xrange(num_workers)]
        #for worker in workers:
            #worker.start()
            #print 'started worker %s' % worker.name

        ## queue up some work to do
        #num_jobs = len(instruments)
        #for symbol, instrument in instruments.items():
            #self.tasks.put(Task(symbol, instrument))
            #print 'job added for %s' % symbol

        ## this tells each worker when to stop and return results
        #for i in xrange(0, num_workers):
            #self.tasks.put(None)

        ## wait for workers to finish and store the results to self
        #self.tasks.join()
        #for i in xrange(num_workers):
            #worker_result = self.results.get()
            #print 'adding bars from worker %i' % i
            #for symbol, bars in worker_result.items():
                #yahoofeed.Feed.add_bars_from_sequence(self, symbol, bars)

#import os
#import datetime
#from collections import defaultdict
#from pyalgotrade import bar
#from pyalgotrade.barfeed import csvfeed


#class Task(object):
    #def __init__(self, symbol, instrument):
        #self.__symbol = symbol
        #self.__instrument = instrument

    #def __call__(self):
        #return self.__symbol, self.__instrument


#class CSVWorker(multiprocessing.Process):
    #def __init__(self, task_queue, result_queue):
        #multiprocessing.Process.__init__(self)
        #self.task_queue = task_queue
        #self.result_queue = result_queue

        #self.__bar_filter = csvfeed.DateRangeFilter(datetime.datetime(2012, 9, 1))
        #self.__row_parser = yahoofeed.RowParser()
        #self.__bars = defaultdict(list)

    #def run(self):
        #while True:
            #next_task = self.task_queue.get()
            #if next_task is None:
                #print '%s: Exiting' % self.name
                #self.task_queue.task_done()
                #self.result_queue.put(self.__bars)
                #break

            #symbol, instrument = next_task()
            #print '%s: %s' % (self.name, instrument)

            #file_path = instrument.get_historical_file_path()
            #if os.path.exists(file_path):
                #with open(file_path) as f:
                    #data = f.read().strip().split('\n')[1:]
                    #try:
                        #for row in data:
                            #if row:
                                #row = row.split(',')
                                #dateTime = datetime.datetime(int(row[0][:4]), int(row[0][5:7]), int(row[0][8:10]))
                                #open_ = float(row[1])
                                #high = float(row[2])
                                #low = float(row[3])
                                #close = float(row[4])
                                #volume = float(row[5])
                                #adj_close = float(row[6])
                                #self.__bars[symbol].append(bar.Bar(dateTime,
                                    #open_, high, low, close, volume, adj_close))
                    #except (AssertionError, ValueError, TypeError):
                        #print 'bad data: %s' % symbol
                        #if symbol in self.__bars.keys():
                            #self.__bars.pop(symbol)
            #self.task_queue.task_done()
        #return
