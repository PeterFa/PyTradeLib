# PyAlgoTrade
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

from google.appengine.ext import db

import hashlib

######################################################################
## Internal helper functions


def get_md5(value):
    m = hashlib.md5()
    m.update(value)
    return m.hexdigest()


class StratExecConfig(db.Model):
    class Status:
        ACTIVE = 1
        FINISHED = 2
        CANCELED_TOO_MANY_ERRORS = 3

    className = db.StringProperty(required=True)
    symbol = db.StringProperty(required=True)
    barType = db.IntegerProperty(required=True)
    firstDate = db.DateTimeProperty(required=True)
    lastDate = db.DateTimeProperty(required=True)
    parameterNames = db.StringListProperty(required=True)
    parameterRanges = db.ListProperty(item_type=int, required=True) # 2 values for each parameter (first, last)
    created = db.DateTimeProperty(required=True)
    status = db.IntegerProperty(required=True)

    # Execution info.
    errors = db.IntegerProperty(default=0) # Number of errors hit.
    totalExecutions = db.IntegerProperty(required=True)
    executionsFinished = db.IntegerProperty(default=0)
    bestResult = db.FloatProperty(required=False)
    bestResultParameters = db.ListProperty(item_type=int, default=None)

    @staticmethod
    def getByKey(key):
        return db.get(key)

    @staticmethod
    def getByClass(className, statusList):
        query = db.GqlQuery("select *"
                            " from StratExecConfig"
                            " where className = :1"
                            " and status in :2"
                            " order by created desc",
                            className, statusList)
        return query.run()

    @staticmethod
    def getByStatus(statusList):
        query = db.GqlQuery("select * from StratExecConfig"
                            " where status in :1"
                            " order by created desc",
                            statusList)
        return query.run()


class Bar(db.Model):
    class Type:
        DAILY = 1

    symbol = db.StringProperty(required=True)
    barType = db.IntegerProperty(required=True)
    date_time = db.DateTimeProperty(required=True)
    open_ = db.FloatProperty(required=True)
    close_ = db.FloatProperty(required=True)
    high = db.FloatProperty(required=True)
    low = db.FloatProperty(required=True)
    volume = db.FloatProperty(required=True)
    adj_close = db.FloatProperty(required=True)

    @staticmethod
    def getKeyName(symbol, barType, date_time):
        return get_md5("%s %s %s" % (symbol, str(barType), str(date_time)))

    @staticmethod
    def getOrCreate(symbol, barType, date_time, open_, close_, high, low, volume, adj_close):
        symbol = symbol.upper()
        keyName = Bar.getKeyName(symbol, barType, date_time)
        return Bar.get_or_insert(key_name=keyName, barType=barType, symbol=symbol, date_time=date_time, open_=open_, close_=close_, high=high, low=low, volume=volume, adj_close=adj_close)

    @staticmethod
    def get_bars(symbol, barType, from_date_time, to_date_time):
        symbol = symbol.upper()
        query = db.GqlQuery("select *"
                            " from Bar"
                            " where symbol = :1"
                            " and barType = :2"
                            " and date_time >= :3"
                            " and date_time <= :4",
                            symbol, barType, from_date_time, to_date_time)
        return query.run()

    @staticmethod
    def hasBars(symbol, barType, from_date_time, to_date_time):
        symbol = symbol.upper()
        query = db.GqlQuery("select *"
                            " from Bar"
                            " where symbol = :1"
                            " and barType = :2"
                            " and date_time >= :3"
                            " and date_time <= :4"
                            " limit 1",
                            symbol, barType, from_date_time, to_date_time)
        return query.get() != None
