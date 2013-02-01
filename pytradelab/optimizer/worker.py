# This file was originally part of PyAlgoTrade.
#
# Copyright 2011 Gabriel Martin Becedillas Ruiz
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

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

import xmlrpclib
import pickle
import time
import socket
import random
import multiprocessing

from pytradelab import optimizer
from pytradelab import barfeed

def call_function(function, *parameters):
    if len(parameters) > 0:
        return function(*parameters)
    else:
        return function()

def call_and_retry_on_network_error(function, retry_count, *parameters):
    ret = None
    while retry_count > 0:
        retry_count -= 1
        try:
            ret = call_function(function, *parameters)
            return ret
        except socket.error:
            time.sleep(random.randint(1, 3))
    ret = call_function(function, *parameters)
    return ret

class Worker:
    def __init__(self, address, port):
        url = "http://%s:%s/PyTradeLabRPC" % (address, port)
        self.__server = xmlrpclib.ServerProxy(url, allow_none=True)
        self.__logger = optimizer.get_logger("server")

    def get_logger(self):
        return self.__logger

    def set_logger(self, logger):
        self.__logger = logger

    def get_symbols_and_bars(self):
        ret = call_and_retry_on_network_error(self.__server.get_symbols_and_bars, 10)
        ret = pickle.loads(ret)
        return ret

    def get_bars_frequency(self):
        ret = call_and_retry_on_network_error(self.__server.get_bars_frequency, 10)
        ret = int(ret)
        return ret

    def get_next_job(self):
        ret = call_and_retry_on_network_error(self.__server.get_next_job, 10)
        ret = pickle.loads(ret)
        return ret

    def push_job_results(self, job_id, result, parameters):
        job_id = pickle.dumps(job_id)
        result = pickle.dumps(result)
        parameters = pickle.dumps(parameters)
        call_and_retry_on_network_error(self.__server.push_job_results, 10, job_id, result, parameters)

    def __process_job(self, job, barsFreq, symbols, bars):
        bestResult = 0
        parameters = job.get_next_parameters()
        bestParams = parameters
        while parameters != None:
            # Wrap the bars into a feed.
            feed = barfeed.OptimizerBarFeed(barsFreq, symbols, bars)
            # Run the strategy.
            self.get_logger().info("Running strategy with parameters %s" % (str(parameters)))
            result = self.run_strategy(feed, *parameters)
            self.get_logger().info("Result %s" % result)
            if result > bestResult:
                bestResult = result
                bestParams = parameters
            # Run with the next set of parameters.
            parameters = job.get_next_parameters()

        assert(bestParams != None)
        self.push_job_results(job.get_id(), bestResult, bestParams)

    # Run the strategy and return the result.
    def run_strategy(self, feed, parameters):
        raise Exception("Not implemented")

    def run(self):
        # Get the symbols and bars.
        symbols, bars = self.get_symbols_and_bars()
        barsFreq = self.get_bars_frequency()

        # Process jobs
        job = self.get_next_job()
        while job != None:
            self.__process_job(job, barsFreq, symbols, bars)
            job = self.get_next_job()

def worker_process(strategy_class, address, port):
    class MyWorker(Worker):
        def run_strategy(self, bar_feed, *parameters):
            strat = strategy_class(bar_feed, *parameters)
            strat.run()
            return strat.get_result()

    # Create a worker and run it.
    w = MyWorker(address, port)
    w.run()

def run(strategy_class, address, port, worker_count = None):
    """Executes one or more worker processes that will run a strategy with the bars and parameters supplied by the server.

    :param strategy_class: The strategy class.
    :param address: The address of the server.
    :type address: string.
    :param port: The port where the server is listening for incoming connections.
    :type port: int.
    :param worker_count: The number of worker processes to run. If None then as many workers as CPUs are used.
    :type worker_count: int.
    """

    assert(worker_count == None or worker_count > 0)
    if worker_count == None:
        worker_count = multiprocessing.cpu_count()

    workers = []
    # Build the worker processes.
    for i in range(worker_count):
        workers.append(multiprocessing.Process(target=worker_process, args=(strategy_class, address, port)))

    # Start workers
    for process in workers:
        process.start()

    # Wait workers
    for process in workers:
        process.join()
