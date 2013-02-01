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

import multiprocessing
import threading
import logging
import socket
import random
from pytradelab import optimizer
from pytradelab.optimizer import server
from pytradelab.optimizer import worker


def server_thread(srv, bar_feed, strategy_parameters, port):
    srv.serve(bar_feed, strategy_parameters)

def worker_process(strategy_class, port):
    class Worker(worker.Worker):
        def run_strategy(self, bar_feed, *parameters):
            strat = strategy_class(bar_feed, *parameters)
            strat.run()
            return strat.get_result()

    # Create a worker and run it.
    w = Worker("localhost", port)
    w.set_logger(optimizer.get_logger("worker", logging.ERROR))
    w.run()

def find_port():
    while True:
        ret = random.randint(1025, 65536)
        try:
            s = socket.socket()
            s.bind(("localhost", ret))
            s.close()
            return ret
        except socket.error:
            pass

def run(strategy_class, bar_feed, strategy_parameters, worker_count=None):
    """Executes many instances of a strategy in parallel and finds the parameters that yield the best results.

    :param strategy_class: The strategy class.
    :param bar_feed: The bar feed to use to backtest the strategy.
    :type bar_feed: :class:`pytradelab.barfeed.BarFeed`.
    :param strategy_parameters: The set of parameters to use for backtesting. An iterable object where **each element is a tuple that holds parameter values**.
    :param worker_count: The number of strategies to run in parallel. If None then as many workers as CPUs are used.
    :type worker_count: int.
    """

    assert(worker_count == None or worker_count > 0)
    if worker_count == None:
        worker_count = multiprocessing.cpu_count()

    workers = []
    port = find_port()
    if port == None:
        raise Exception("Failed to find a port to listen")

    # Build and start the server thread before the worker processes. We'll manually stop the server once workers have finished.
    srv = server.Server("localhost", port, False)
    server_thread = threading.Thread(target=server_thread, args=(srv, bar_feed, strategy_parameters, port))
    server_thread.start()

    try:
        # Build the worker processes.
        for i in range(worker_count):
            workers.append(multiprocessing.Process(target=worker_process, args=(strategy_class, port)))

        # Start workers
        for process in workers:
            process.start()

        # Wait workers
        for process in workers:
            process.join()

    finally:
        # Stop and wait the server to finish.
        srv.stop()
        server_thread.join()
