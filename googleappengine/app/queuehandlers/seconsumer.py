# This file was originally part of PyAlgoTrade.
#
# Copyright 2012 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import taskqueue
from google.appengine.api import memcache

import pickle
import zlib
import traceback

from pytradelab import barfeed
from pytradelab.barfeed import membf
from pytradelab import bar
import persistence
from queuehandlers import seresult
from common import cls
from common import timer
import common.logger


# Converts a persistence.Bar to a pytradelab.bar.Bar.
def ds_bar_to_pytradelab_bar(dsBar):
    return bar.Bar(dsBar.date_time, dsBar.open_, dsBar.high, dsBar.low, dsBar.close_, dsBar.volume, dsBar.adj_close)

# Loads pytradelab.bar.Bars objects from the db.
def load_pytradelab_daily_bars(symbol, barType, from_date_time, to_date_time):
    assert(barType == persistence.Bar.Type.DAILY)
    # Load pytradelab.bar.Bar objects from the db.
    dbBars = persistence.Bar.get_bars(symbol, barType, from_date_time, to_date_time)
    bars = [ds_bar_to_pytradelab_bar(dbBar) for dbBar in dbBars]

    # Use a feed to build pytradelab.bar.Bars objects.
    feed = membf.Feed(barfeed.Frequency.DAY)
    feed.add_bars_from_sequence(symbol, bars)
    ret = []
    feed.start()
    for bars in feed:
        ret.append(bars)
    feed.stop()
    feed.join()
    return ret


class BarsCache:
    def __init__(self, logger):
        self.__cache = {}
        self.__logger = logger

    def __addLocal(self, key, bars):
        self.__cache[key] = bars

    def __getLocal(self, key):
        return self.__cache.get(key, None)

    def __addToMemCache(self, key, bars):
        try:
            value = str(pickle.dumps(bars))
            value = zlib.compress(value, 9)
            memcache.add(key=key, value=value)
        except Exception, e:
            self.__logger.error("Failed to add bars to memcache: %s" % e)

    def __getFromMemCache(self, key):
        ret = None
        try:
            value = memcache.get(key)
            if value != None:
                value = zlib.decompress(value)
                ret = pickle.loads(value)
        except Exception, e:
            self.__logger.error("Failed to load bars from memcache: %s" % e)
        return ret

    def add(self, key, bars):
        key = str(key)
        self.__addLocal(key, bars)
        self.__addToMemCache(key, bars)

    def get(self, key):
        key = str(key)
        ret = self.__getLocal(key)
        if ret == None:
            ret = self.__getFromMemCache(key)
            if ret != None:
                # Store in local cache for later use.
                self.__addLocal(key, ret)
        return ret


class StrategyExecutor:
    def __init__(self):
        self.__logger = common.logger.Logger()
        self.__barCache = BarsCache(self.__logger)

    def __load_bars(self, stratExecConfig):
        ret = self.__barCache.get(stratExecConfig.key())
        if ret == None:
            self.__logger.info("Loading '%s' bars from %s to %s" % (stratExecConfig.symbol, stratExecConfig.firstDate, stratExecConfig.lastDate))
            ret = load_pytradelab_daily_bars(stratExecConfig.symbol, stratExecConfig.barType, stratExecConfig.firstDate, stratExecConfig.lastDate)
            self.__barCache.add(stratExecConfig.key(), ret)
        return ret

    def get_logger(self):
        return self.__logger

    def run_strategy(self, stratExecConfig, paramValues):
        bars = self.__load_bars(stratExecConfig)

        bar_feed = barfeed.OptimizerBarFeed(barfeed.Frequency.DAY, [stratExecConfig.symbol], bars)

        # Evaluate the strategy with the feed bars.
        params = [bar_feed]
        params.extend(paramValues)
        myStrategy = cls.Class(stratExecConfig.className).getClass()(*params)
        myStrategy.run()
        return myStrategy.get_result()


class SEConsumerHandler(webapp.RequestHandler):
    url = "/queue/seconsumer"
    default_batch_size = 200

    class Params:
        stratExecConfigKeyParam = 'stratExecConfigKey'
        paramsItParam = 'paramsIt'
        batchSizeParam = 'batchSize'

    @staticmethod
    def queue(stratExecConfigKey, paramsIt, batchSize):
        params = {}
        params[SEConsumerHandler.Params.stratExecConfigKeyParam] = stratExecConfigKey
        params[SEConsumerHandler.Params.paramsItParam] = pickle.dumps(paramsIt)
        params[SEConsumerHandler.Params.batchSizeParam] = batchSize
        taskqueue.add(queue_name="se-consumer-queue", url=SEConsumerHandler.url, params=params)

    def post(self):
        global strategyExecutor

        tmr = timer.Timer()
        stratExecConfigKey = self.request.get(SEConsumerHandler.Params.stratExecConfigKeyParam)
        paramsIt = pickle.loads(str(self.request.get(SEConsumerHandler.Params.paramsItParam)))
        batchSize = int(self.request.get(SEConsumerHandler.Params.batchSizeParam))
        stratExecConfig = persistence.StratExecConfig.getByKey(stratExecConfigKey)

        bestResult = 0
        bestResultParams = []
        executionsLeft = batchSize 
        errors = 0 
        while executionsLeft > 0:
            try:
                paramValues = paramsIt.getCurrent()

                # If there are no more parameters, just stop.
                if paramValues == None:
                    break

                result = strategyExecutor.run_strategy(stratExecConfig, paramValues)
                if result > bestResult:
                    bestResult = result
                    bestResultParams = paramValues
            except Exception, e:
                errors += 1
                strategyExecutor.get_logger().error("Error executing strategy '%s' with parameters %s: %s" % (stratExecConfig.className, paramValues, e))
                strategyExecutor.get_logger().error(traceback.format_exc())

            executionsLeft -= 1
            paramsIt.moveNext()

            # Stop executing before we ran out of time. I'm assuming that strategies take less than 1 minute to execute.
            if tmr.minutesElapsed() > 9 and executionsLeft > 0:
                strategyExecutor.get_logger().info("Rescheduling. %d executions left." % executionsLeft)
                SEConsumerHandler.queue(stratExecConfigKey, paramsIt, executionsLeft)
                break

        # Queue the results.
        seresult.SEResultHandler.queue(stratExecConfigKey, bestResult, bestResultParams, batchSize - executionsLeft, errors)

# This is global to reuse previously loaded bars.
strategyExecutor = StrategyExecutor()

def main():
    _handlers = [
            (SEConsumerHandler.url, SEConsumerHandler)
            ]
    application = webapp.WSGIApplication(_handlers, debug=True)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
