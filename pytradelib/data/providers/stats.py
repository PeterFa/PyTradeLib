# This file is part of PyTradeLib.
#
# Copyright 2013 Brian A Cappello <briancappello at gmail>
#
# PyTradeLib is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyTradeLib is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyTradeLib.  If not, see http://www.gnu.org/licenses/

import urllib
import datetime

try: import simplejson as json
except: import json

from pytradelib import utils
from pytradelib.data import db
from pytradelib.data import providers
from pytradelib.data.providers.index import YQLMixin
from pytradelib.failed import Symbols as FailedSymbols


class Provider(YQLMixin, providers.Provider):
    def __init__(self):
        self.__custom_keys = []
        self.__yahoo_to_keys = {
            'Symbol': 'symbol',
            'DividendPayDate': 'dividend_pay_date',
            'ExDividendDate': 'ex_dividend_date',
            'DividendShare': 'dividend_share',
            'DividendYield': 'dividend_yield',
            'AverageDailyVolume': 'average_daily_volume',
            'BookValue': 'book_value',
            'EBITDA': 'ebitda',
            'EarningsShare': 'earnings_per_share',
            'FiftydayMovingAverage': 'ma_50',
            'TwoHundreddayMovingAverage': 'ma_200',
            'LastTradeDateTime': 'last_trade_datetime',
            'LastTradePriceOnly': 'last_trade_price',
            'Volume': 'last_trade_volume',
            'MarketCapitalization': 'market_cap',
            'Name': 'name',
            'PEGRatio': 'peg_ratio',
            'PERatio': 'pe_ratio',
            'PriceBook': 'price_per_book',
            'PriceSales': 'price_per_sales',
            'ShortRatio': 'short_ratio',
            'StockExchange': 'exchange',
            'YearHigh': 'year_high',
            'YearLow': 'year_low',
            }

        self.__keys_to_yahoo = dict(zip(self.__yahoo_to_keys.values(),
                                        self.__yahoo_to_keys.keys()))
    @property
    def name(self):
        return 'YahooStats'

    @property
    def properties(self):
        # return properties with Yahoo's names
        props = self.__yahoo_to_keys.keys()
        if self.__custom_keys:
            props = self.__custom_keys
        if 'ErrorIndicationreturnedforsymbolchangedinvalid' not in props:
            props.append('ErrorIndicationreturnedforsymbolchangedinvalid')
        if 'Symbol' not in props:
            props.append('Symbol')
        if 'LastTradeDateTime' in props:
            props.pop(props.index('LastTradeDateTime'))
            if 'LastTradeDate' not in props:
                props.append('LastTradeDate')
            if 'LastTradeTime' not in props:
                props.append('LastTradeTime')
        return props

    @properties.setter
    def set_properties(self, keys):
        for key in keys:
            assert key in self.__keys_to_yahoo, 'invalid property "%s"' % key
        self.__custom_keys = [self.__keys_to_yahoo[key] for key in keys]

    def get_url(self, symbols, context=None):
        context = context or {}
        yql = 'select %s from yahoo.finance.quotes where symbol in (%s)' % (
            ','.join(self.properties),
            ','.join(['"%s"' % symbol.upper() for symbol in symbols]))
        context['validate_field'] = 'quote'
        context['yql'] = yql
        url = self._get_yql_url(yql)
        return url, context

    def get_urls(self, symbols):
        if not isinstance(symbols, list):
            symbols = [symbols]
        ret = [self.get_url(x) for x in utils.batch(symbols, size=20)]
        return ret

    def __verify_symbol_stats(self, symbol_key_stats):
        error = symbol_key_stats.pop('ErrorIndicationreturnedforsymbolchangedinvalid')
        if error:
            if 'No such ticker symbol' in error:
                error = 'No such ticker symbol.'
            elif 'Ticker symbol has changed to' in error:
                new_symbol = error.strip()[:-1]
                new_symbol = new_symbol[new_symbol.rfind('>')+1:new_symbol.rfind('<')]
                error = 'Ticker symbol has changed to %s.' % new_symbol
            FailedSymbols.add_failed(symbol_key_stats['Symbol'], error)
            return False
        return True

    def verify_download(self, data_context):
        for data, context in YQLMixin.verify_download(self, data_context):
            remove_indexes = []
            for i, symbol_stats in enumerate(data):
                if not self.__verify_symbol_stats(symbol_stats):
                    remove_indexes.insert(0, i)
            for i in remove_indexes:
                data.pop(i)
            if data:
                for stats in data:
                    yield stats

    def process_downloaded_data(self, symbol_stats):
        for stats in symbol_stats:
            self.__clean_last_trade_date_times(stats)
            self.__clean_dividend_dates(stats)
            utils.try_dict_str_values_to_float(stats)
            
            # convert key names to those used internally by pytradelib
            for key in stats.keys():
                value = stats.pop(key)
                if key in self.__yahoo_to_keys:
                    stats[self.__yahoo_to_keys[key]] = value
            yield stats

    def __clean_last_trade_date_times(self, stats):
        # convert last trade date/times to python datetime objects
        if 'LastTradeDate' in stats or 'LastTradeTime' in stats:
            valid_quote_date_time = True
            if 'LastTradeDate' in stats:
                try:
                    last_trade_date = stats['LastTradeDate']
                    last_trade_date = datetime.datetime.strptime(last_trade_date, '%m/%d/%Y').date()
                    stats['LastTradeDate'] = last_trade_date
                except (TypeError, ValueError):
                    stats['LastTradeDate'] = None
                    valid_quote_date_time = False

            if 'LastTradeTime' in stats:
                try:
                    last_trade_time = stats['LastTradeTime']
                    last_trade_time = datetime.datetime.strptime(last_trade_time, '%I:%M%p').time() # delayed ~15mins!
                    stats['LastTradeTime'] = last_trade_time
                except (TypeError, ValueError):
                    stats['LastTradeTime'] = None
                    valid_quote_date_time = False

            if valid_quote_date_time:
                dateTime = datetime.datetime.combine(last_trade_date, last_trade_time) # delayed ~15mins!
                stats['LastTradeDateTime'] = dateTime
            else:
                stats['LastTradeDateTime'] = None

    def __clean_dividend_dates(self, stats):
        # convert dividend related dates to python datetime objects
        if 'DividendPayDate' in stats and 'ExDividendDate' in stats:
            # yahoo provides dividend related dates without an explicit year.
            # these functions help by assuming the current year and adjusting as necessary
            def get_date_from_month_and_day(date_str):
                if date_str == None:
                    return None
                return datetime.datetime.strptime(' '.join([
                    date_str, str(datetime.date.today().year)]), '%b %d %Y').date()

            def adjust_year(date, adjustment):
                try:
                    return datetime.date(date.year + adjustment, date.month, date.day)
                except ValueError, e:
                    if 'day is out of range for month' in str(e):
                        return datetime.date(date.year + adjustment, date.month, date.day-1)
                    raise e

            dividend_pay_date = stats['DividendPayDate']
            if dividend_pay_date != None:
                # convert the dividend pay date to a datetime.date and make sure its year is valid
                if '-' not in dividend_pay_date:
                    dividend_pay_date = get_date_from_month_and_day(dividend_pay_date)
                    if dividend_pay_date < datetime.date.today():
                        dividend_pay_date = adjust_year(dividend_pay_date, 1)
                else:
                    dividend_pay_date = datetime.datetime.strptime(
                        stats['DividendPayDate'], '%d-%b-%y').date()

                # convert the ex-dividend date to a datetime.date and make sure its year is valid
                ex_dividend_date = stats['ExDividendDate']
                if ex_dividend_date:
                    if '-' not in ex_dividend_date:
                        ex_dividend_date = get_date_from_month_and_day(ex_dividend_date)
                        while(ex_dividend_date >= dividend_pay_date):
                            ex_dividend_date = adjust_year(ex_dividend_date, -1)
                    else:
                        ex_dividend_date = datetime.datetime.strptime(
                            stats['ExDividendDate'], '%d-%b-%y').date()
                stats['DividendPayDate'] = dividend_pay_date
                stats['ExDividendDate'] = ex_dividend_date
            else:
                stats['DividendPayDate'] = None
                stats['ExDividendDate'] = None
                stats['DividendShare'] = None
                stats['DividendYield'] = None

    def save_data(self, data_context):
        stats = [x for x, context in data_context]
        self._db.insert_or_update_stats(stats)
        yield context

if __name__ == '__main__':
    _db = db.Database()
    _downloader = Provider()
    urls = _downloader.get_urls(_db.get_symbols())
    symbol_stats = \
        _downloader.process_downloaded_data(
            _downloader.verify_download(
                utils.bulk_download(urls)))
    final_context = [d for d in symbol_stats][0]
