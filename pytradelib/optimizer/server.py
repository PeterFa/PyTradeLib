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

import SimpleXMLRPCServer
import threading
import time
import pickle
import random
from pytradelib import optimizer


class AutoStopThread(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.__server = server

    def run(self):
        while self.__server.jobs_pending():
            time.sleep(1)
        self.__server.stop()


class Results(object):
    """The results of the strategy executions."""
    def __init__(self, parameters, result):
        self.__parameters = parameters
        self.__result = result

    def get_parameters(self):
        """Returns a sequence of parameter values."""
        return self.__parameters

    def get_result(self):
        """Returns the result for a given set of parameters."""
        return self.__result


class Job(object):
    def __init__(self, strategy_parameters):
        self.__strategy_parameters = strategy_parameters
        self.__best_result = None
        self.__best_parameters = None
        self.__id = id(self)

    def get_id(self):
        return self.__id

    def get_next_parameters(self):
        ret = None
        if len(self.__strategy_parameters):
            ret = self.__strategy_parameters.pop()
        return ret

    def get_best_parameters(self):
        return self.__best_parameters

    def get_best_result(self):
        return self.__best_result

    def set_best_result(self, result, parameters):
        self.__best_result = result
        self.__best_parameters = parameters

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    rpc_paths = ('/PyTradeLibRPC',)

class Server(SimpleXMLRPCServer.SimpleXMLRPCServer):
    default_batch_size = 200

    def __init__(self, address, port, auto_stop=True):
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, (address, port), requestHandler=RequestHandler, logRequests=False, allow_none=True)

        self.__symbols_and_bars = None # Pickle'd symbols and bars for faster retrieval.
        self.__bars_freq = None
        self.__active_jobs = {}
        self.__active_jobs_lock = threading.Lock()
        self.__parameters_lock = threading.Lock()
        self.__best_job = None
        self.__parameters_iterator = None
        self.__logger = optimizer.get_logger("server")
        if auto_stop:
            self.__auto_stop_thread = AutoStopThread(self)
        else:
            self.__auto_stop_thread = None

        self.register_introspection_functions()
        self.register_function(self.get_symbols_and_bars, 'get_symbols_and_bars')
        self.register_function(self.get_bars_frequency, 'get_bars_frequency')
        self.register_function(self.get_next_job, 'get_next_job')
        self.register_function(self.push_job_results, 'push_job_results')
        self.__forced_stop = False

    def __get_random_active_job(self):
        ret = None
        with self.__active_jobs_lock:
            if len(self.__active_jobs) > 0:
                ret = random.choice(self.__active_jobs.values())
        return ret

    def __get_next_parameters(self):
        ret = []
        # Get the next set of parameters.
        with self.__parameters_lock:
            if self.__parameters_iterator != None:
                try:
                    for i in xrange(Server.default_batch_size):
                        ret.append(self.__parameters_iterator.next())
                except StopIteration:
                    self.__parameters_iterator = None
        return ret

    def get_logger(self):
        return self.__logger

    def set_logger(self, logger):
        self.__logger = logger

    def get_symbols_and_bars(self):
        return self.__symbols_and_bars

    def get_bars_frequency(self):
        return str(self.__bars_freq)

    def get_best_job(self):
        return self.__best_job

    def get_next_job(self):
        ret = None
        params = []

        # Get the next set of parameters.
        params = self.__get_next_parameters()

        # Map the active job
        if len(params):
            ret = Job(params)
            with self.__active_jobs_lock:
                self.__active_jobs[ret.get_id()] = ret

        # If there are no more parameters, try to resubmit any active job.
        # if ret == None:
        # 	ret = self.__get_random_active_job()

        return pickle.dumps(ret)

    def jobs_pending(self):
        if self.__forced_stop:
            return False

        with self.__parameters_lock:
            jobs_pending = self.__parameters_iterator != None
        with self.__active_jobs_lock:
            activeJobs = len(self.__active_jobs) > 0
        return jobs_pending or activeJobs

    def push_job_results(self, job_id, result, parameters):
        job_id = pickle.loads(job_id)
        result = pickle.loads(result)
        parameters = pickle.loads(parameters)

        job = None

        # Get the active job and remove the mapping.
        with self.__active_jobs_lock:
            try:
                job = self.__active_jobs[job_id]
                del self.__active_jobs[job_id]
            except KeyError:
                # The job's results were already submitted.
                return

        # Save the job with the best result
        if self.__best_job == None or result > self.__best_job.get_best_result():
            job.set_best_result(result, parameters)
            self.__best_job = job

        self.get_logger().info("Partial result $%.2f with parameters: %s" % (result, parameters))

    def stop(self):
        self.shutdown()

    def serve(self, bar_feed, strategy_parameters):
        ret = None
        try:
            # Initialize symbols, bars and parameters.
            self.get_logger().info("Loading bars")
            loaded_bars = []
            bar_feed.start()
            for bars in bar_feed:
                loaded_bars.append(bars)
            bar_feed.stop()
            bar_feed.join()
            symbols = bar_feed.get_registered_symbols()
            self.__symbols_and_bars = pickle.dumps((symbols, loaded_bars))
            self.__bars_freq = bar_feed.get_frequency()

            self.__parameters_iterator = iter(strategy_parameters)

            if self.__auto_stop_thread:
                self.__auto_stop_thread.start()

            self.get_logger().info("Waiting for workers")
            self.serve_forever()

            if self.__auto_stop_thread:
                self.__auto_stop_thread.join()

            # Show the best result.
            best_job = self.get_best_job()
            if best_job:
                self.get_logger().info("Best final result $%.2f with parameters: %s" % (best_job.get_best_result(), best_job.get_best_parameters()))
                ret = Results(best_job.get_best_parameters(), best_job.get_best_result())
            else:
                self.get_logger().error("No jobs processed")
        finally:
            self.__forced_stop = True
        return ret


def serve(bar_feed, strategy_parameters, address, port):
    """Executes a server that will provide bars and strategy parameters for workers to use.

    :param bar_feed: The bar feed that each worker will use to backtest the strategy.
    :type bar_feed: :class:`pytradelib.barfeed.BarFeed`.
    :param strategy_parameters: The set of parameters to use for backtesting. An iterable object where **each element is a tuple that holds parameter values**.
    :param address: The address to listen for incoming worker connections.
    :type address: string.
    :param port: The port to listen for incoming worker connections.
    :type port: int.
    :rtype: A :class:`Results` instance with the best results found.
    """
    s = Server(address, port)
    return s.serve(bar_feed, strategy_parameters)
