# This file is part of PyTradeLab.
#
# Copyright 2013 Brian A Cappello <briancappello at gmail>
#
# PyTradeLab is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyTradeLab is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with PyTradeLab.  If not, see http://www.gnu.org/licenses/

import urllib
import datetime

try: import simplejson as json
except: import json

from pytradelab import utils
from pytradelab.failed import Symbols as FailedSymbols


def __get_yql_url(yql):
    base_url = 'http://query.yahooapis.com/v1/public/yql'
    query = urllib.urlencode({
        'q': yql,
        'env': 'store://datatables.org/alltableswithkeys',
        'format': 'json' })
    return ''.join([base_url, '?', query])

def __verify_json_data(json_data, validate_field):
    if json_data and isinstance(json_data, dict):
        if 'error' in json_data:
            print 'Query failed for %s: %s' % (yql, json_data['error']['description'])
            return None
        if 'query' in json_data:
            query = json_data['query']
            if query and 'results' in query:
                results = query['results']
                if validate_field in results:
                    return results[validate_field]
                else:
                    print 'got results for "%s" but none valid:\n%s' % (yql, json_data)
            else:
                print 'no results for "%s":\n%s' % (yql, json_data)
        else:
            print '"query" not in "%s":\n%s' % (yql, json_data)
    else:
        print 'invalid data returned for "%s":\n%s' % (yql, json_data)
    return None

def execute_yql(yql_queries, validate_field):
    ''' Downloads, verifies, and returns the json data for the supplied yql query(s).

    :param yql_queries: the YQL query string(s) to be downloaded. they must share the same validate field.
    :type yql_queries: string or list of strings
    :param validate_field: the key to use to retrieve valid results data from the downloaded json
    :type validate_field: string
    '''
    if not isinstance(yql_queries, list):
        yql_queries = [yql_queries]
    ret = []
    for data, tag_error_dict in utils.bulk_download(
        [__get_yql_url(yql) for yql in yql_queries]
    ):
        url = tag_error_dict['tag']
        if 'error' not in tag_error_dict:
            json_data = __verify_json_data(json.loads(data), validate_field)
            if json_data:
                if isinstance(json_data, list):
                    ret.extend(json_data)
                else:
                    ret.append(json_data)
        else:
            print 'Error downloading "%s": %s' % (url, tag_error_dict['error'])
    return ret


class SymbolIndex(object):
    def get_symbols(self):
        ''' Returns a list of all the symbols supported by Yahoo.
        '''
        return sorted(self.get_data()['all_symbols'].keys())

    def get_data(self):
        ''' Returns a dict with the following key/value pairs:
        'sectors': ['sector names']
        'industry_sectors': [('industry names', 'sector names')]
        'symbols': [{ keys: symbol, name, industry }]
        '''
        ret = {
            'sectors': [],
            'industry_sectors': [],
            'symbols': [],
            }
        yql = 'select * from yahoo.finance.sectors'
        json_sector_list = execute_yql(yql, 'sector')
        ret = self.__parse_sector_industries(json_sector_list, ret)
        yql_queries = []
        for ids in utils.batch(ret.pop('industry_ids'), size=10):
            yql = 'select * from yahoo.finance.industry where id in (%s)' % ','.join(
                ['"%s"' % i for i in ids])
            yql_queries.append(yql)
        json_industry_list = execute_yql(yql_queries, 'industry')
        return self.__parse_industry_symbols(json_industry_list, ret)

    def __parse_sector_industries(self, json_sector_list, ret):
        ret['industry_ids'] = [] # a temporary list to be popped off by self.get_data()
        for sector in json_sector_list:
            sector_name = sector['name']
            ret['sectors'].append(sector_name)
            industries = sector['industry']
            if not isinstance(industries, list):
                industries = [industries]
            for industry in industries:
                ret['industry_ids'].append(industry['id'])
                ret['industry_sectors'].append((industry['name'], sector_name))
        return ret

    def __parse_industry_symbols(self, json_industry_list, ret):
        for json_industry in json_industry_list:
            if 'company' in json_industry:
                for json_instrument in json_industry['company']:
                    if isinstance(json_instrument, dict):
                        ret['symbols'].append({
                            'symbol': json_instrument['symbol'].lower(),
                            'name': json_instrument['name'].encode('utf-8'),
                            'industry': json_industry['name'],
                            })
        return ret

SymbolIndex = SymbolIndex()


class KeyStats(object):
    def __init__(self):
        self.__custom_key_stats_properties = None
        self.__key_stats_properties = [
            'Symbol',
            'ErrorIndicationreturnedforsymbolchangedinvalid',

            # delayed quote properties
            # WARNING: quote properties will return None from very early morning EST until market open
            #'AfterHoursChangeRealtime', # does this work, even for just delayed data?
            #'BidRealtime',        # delayed ~15 minutes
            #'AskRealtime',        # delayed ~15 minutes
            'LastTradeDate',      # delayed ~15 minutes (should be downloaded with LastTradeTime)
            'LastTradeTime',      # delayed ~15 minutes (should be downloaded with LastTradeDate)
            #'Open',               # delayed ~15 minutes
            #'DaysHigh',           # delayed ~15 minutes
            #'DaysLow',            # delayed ~15 minutes
            'LastTradePriceOnly', # delayed ~15 minutes
            'Volume',             # delayed ~15 minutes
            #'PercentChange',      # delayed ~15 minutes
            #'PreviousClose',

            # all dividend properties should be downloaded together
            'DividendPayDate',
            'ExDividendDate',
            'DividendShare',
            'DividendYield',

            # key stats properties
            'AverageDailyVolume',
            'BookValue',
            'EBITDA',
            'EarningsShare',
            #'EPSEstimateCurrentYear',
            #'EPSEstimateNextQuarter',
            #'EPSEstimateNextYear',
            'FiftydayMovingAverage',
            'MarketCapitalization',
            'Name', # sometimes better than what's provided by SymbolIndex.get_data()
            'PEGRatio',
            'PERatio',
            'PriceBook',
            'PriceSales',
            'ShortRatio',
            'StockExchange',
            'TwoHundreddayMovingAverage',
            'YearHigh',
            'YearLow',
            ]

        self.__key_lookup = {
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
            'LastTradePriceOnly': 'last_price',
            'Volume': 'volume',
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

        self.__reverse_key_lookup = dict(zip(self.__key_lookup.values(), self.__key_lookup.keys()))

    def keys(self):
        return self.__key_stats_properties

    def set_key_stats_properties(self, properties):
        ''' Sets the key stats YQL property keys to download.
        '''
        props = {}
        for key in properties:
            props[self.__reverse_key_lookup[key]] = properties[key]
        if 'Symbol' not in props:
            props.append('Symbol')
        if 'ErrorIndicationreturnedforsymbolchangedinvalid' not in props:
            props.append('ErrorIndicationreturnedforsymbolchangedinvalid')
        self.__custom_key_stats_properties = props

    def get_data(self, symbols):
        ''' Returns a dict where the keys are symbols and the values are dicts
            with keys of keystats property names and values of results.

        :param symbols: the symbol(s) to download key stats for.
        :type symbols: string or list of strings
        '''
        if not isinstance(symbols, list):
            symbols = [symbols]
        ret = {}
        yql_queries = []
        properties = self.__custom_key_stats_properties or self.__key_stats_properties
        for symbol_batch in utils.batch(symbols, size=300):
            yql = 'select %s from yahoo.finance.quotes where symbol in (%s)' % (
                ','.join(properties),
                ','.join(['"%s"' % symbol.upper() for symbol in symbols]))
            yql_queries.append(yql)
        for symbol_key_stats in execute_yql(yql_queries, 'quote'):
            if self.__verify_key_stats(symbol_key_stats):
                ret[symbol_key_stats['symbol']] = self.__parse_key_stats(symbol_key_stats)
        return ret

    def __verify_key_stats(self, symbol_key_stats):
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

    def __parse_key_stats(self, json_stats):
        # convert last trade date/times to python datetime objects
        if 'LastTradeDate' in json_stats or 'LastTradeTime' in json_stats:
            valid_quote_date_time = True
            if 'LastTradeDate' in json_stats:
                try:
                    last_trade_date = json_stats['LastTradeDate']
                    last_trade_date = datetime.datetime.strptime(last_trade_date, '%m/%d/%Y').date()
                    json_stats['LastTradeDate'] = last_trade_date
                except (TypeError, ValueError):
                    json_stats['LastTradeDate'] = None
                    valid_quote_date_time = False

            if 'LastTradeTime' in json_stats:
                try:
                    last_trade_time = json_stats['LastTradeTime']
                    last_trade_time = datetime.datetime.strptime(last_trade_time, '%I:%M%p').time() # delayed ~15mins!
                    json_stats['LastTradeTime'] = last_trade_time
                except (TypeError, ValueError):
                    json_stats['LastTradeTime'] = None
                    valid_quote_date_time = False

            if valid_quote_date_time:
                dateTime = datetime.datetime.combine(last_trade_date, last_trade_time) # delayed ~15mins!
                json_stats['LastTradeDateTime'] = dateTime
            else:
                json_stats['LastTradeDateTime'] = None

        # convert dividend related dates to python datetime objects
        if 'DividendPayDate' in json_stats and 'ExDividendDate' in json_stats:
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

            dividend_pay_date = json_stats['DividendPayDate']
            if dividend_pay_date != None:
                # convert the dividend pay date to a datetime.date and make sure its year is valid
                if '-' not in dividend_pay_date:
                    dividend_pay_date = get_date_from_month_and_day(dividend_pay_date)
                    if dividend_pay_date < datetime.date.today():
                        dividend_pay_date = adjust_year(dividend_pay_date, 1)
                else:
                    dividend_pay_date = datetime.datetime.strptime(
                        json_stats['DividendPayDate'], '%d-%b-%y').date()

                # convert the ex-dividend date to a datetime.date and make sure its year is valid
                ex_dividend_date = json_stats['ExDividendDate']
                if ex_dividend_date:
                    if '-' not in ex_dividend_date:
                        ex_dividend_date = get_date_from_month_and_day(ex_dividend_date)
                        while(ex_dividend_date >= dividend_pay_date):
                            ex_dividend_date = adjust_year(ex_dividend_date, -1)
                    else:
                        ex_dividend_date = datetime.datetime.strptime(
                            json_stats['ExDividendDate'], '%d-%b-%y').date()
                json_stats['DividendPayDate'] = dividend_pay_date
                json_stats['ExDividendDate'] = ex_dividend_date
            else:
                json_stats['DividendPayDate'] = None
                json_stats['ExDividendDate'] = None
                json_stats['DividendShare'] = None
                json_stats['DividendYield'] = None

        # convert numbers to python floats
        ret = utils.try_dict_str_values_to_float(json_stats)
        
        # convert key names to those used internally by pytradelab
        for key in ret.keys():
            value = ret.pop(key)
            if key in self.__key_lookup:
                ret[self.__key_lookup[key]] = value
        return ret

KeyStats = KeyStats()
