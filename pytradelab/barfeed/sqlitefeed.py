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

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

from pytradelab.barfeed import dbfeed
from pytradelab.barfeed import membf
from pytradelab import bar
from pytradelab.utils import dt

import sqlite3
import os

def normalize_symbol(symbol):
    return symbol.upper()

# SQLite DB.
# Timestamps are stored in UTC.
class Database(dbfeed.Database):
    def __init__(self, db_file_path):
        self.__symbol_ids = {}

        # If the file doesn't exist, we'll create it and initialize it.
        initialize = False
        if not os.path.exists(db_file_path):
            initialize = True
        self.__connection = sqlite3.connect(db_file_path)
        self.__connection.isolation_level = None # To do auto-commit
        if initialize:
            self.create_schema()

    def __find_symbol_id(self, symbol):
        cursor = self.__connection.cursor()
        sql = "select symbol_id from symbol where name = ?"
        cursor.execute(sql, [symbol])
        ret = cursor.fetchone()
        if ret != None:
            ret = ret[0]
        cursor.close()
        return ret

    def __add_symbol(self, symbol):
        ret =  self.__connection.execute("insert into symbol (name) values (?)", [symbol])
        return ret.lastrowid

    def __get_or_create_symbol(self, symbol):
        # Try to get the symbol id from the cache.
        ret = self.__symbol_ids.get(symbol, None)
        if ret != None:
            return ret
        # If its not cached, get it from the db.
        ret = self.__find_symbol_id(symbol)
        # If its not in the db, add it.
        if ret == None:
            ret = self.__add_symbol(symbol)
        # Cache the id.
        self.__symbol_ids[symbol] = ret
        return ret

    def create_schema(self):
        self.__connection.execute("create table symbol ("
            + "symbol_id integer primary key autoincrement"
            + ", name text unique not null)")

        self.__connection.execute("create table bar ("
            + "symbol_id integer references symbol (symbol_id)"
            + ",frequency integer not null"
            + ",timestamp integer not null"
            + ",open real not null"
            + ",high real not null"
            + ",low real not null"
            + ",close real not null"
            + ",volume real not null"
            + ",adj_close real"
            + ",primary key (symbol_id, frequency, timestamp))" )

    def add_bar(self, symbol, bar, frequency):
        symbol = normalize_symbol(symbol)
        symbol_id = self.__get_or_create_symbol(symbol)
        time_stamp = dt.datetime_to_timestamp(bar.get_date_time())

        try:
            sql = "insert into bar (symbol_id, frequency, timestamp, open, high, low, close, volume, adj_close) values (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            params = [symbol_id, frequency, time_stamp, bar.get_open(), bar.get_high(), bar.get_low(), bar.get_close(), bar.get_volume(), bar.get_adj_close()]
            self.__connection.execute(sql, params)
        except sqlite3.IntegrityError:
            sql = "update bar set open = ?, high = ?, low = ?, close = ?, volume = ?, adj_close = ?" \
                    " where symbol_id = ? and frequency = ? and timestamp = ?"
            params = [bar.get_open(), bar.get_high(), bar.get_low(), bar.get_close(), bar.get_volume(), bar.get_adj_close(), symbol_id, frequency, time_stamp]
            self.__connection.execute(sql, params)

    def get_bars(self, symbol, frequency, timezone = None, from_date_time = None, to_date_time = None):
        symbol = normalize_symbol(symbol)
        sql = "select bar.timestamp, bar.open, bar.high, bar.low, bar.close, bar.volume, bar.adj_close" \
                " from bar join symbol on (bar.symbol_id = symbol.symbol_id)" \
                " where symbol.name = ? and bar.frequency = ?"
        args = [symbol, frequency]

        if from_date_time != None:
            sql += " and bar.timestamp >= ?"
            args.append(dt.datetime_to_timestamp(from_date_time))
        if to_date_time != None:
            sql += " and bar.timestamp <= ?"
            args.append(dt.datetime_to_timestamp(to_date_time))

        sql += " order by bar.timestamp asc"
        cursor = self.__connection.cursor()
        cursor.execute(sql, args)
        ret = []
        for row in cursor:
            date_time = dt.timestamp_to_datetime(row[0])
            if timezone:
                date_time = dt.localize(date_time, timezone)
            ret.append(bar.Bar(date_time, row[1], row[2], row[3], row[4], row[5], row[6]))
        cursor.close()
        return ret

class Feed(membf.Feed):
    def __init__(self, db_file_path, frequency):
        membf.Feed.__init__(self, frequency)
        self.__db = Database(db_file_path)

    def get_database(self):
        return self.__db

    def load_bars(self, symbol, timezone = None, from_date_time = None, to_date_time = None):
        bars = self.__db.get_bars(symbol, self.get_frequency(), timezone, from_date_time, to_date_time)
        self.add_bars_from_sequence(symbol, bars)

