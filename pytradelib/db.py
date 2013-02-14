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

import os
import sqlite3

from collections import OrderedDict
from pytradelib import utils
from pytradelib import settings


class Database(object):
    def __init__(self, db_file_path=None):
        if db_file_path is None:
            db_file_path = os.path.join(settings.DATA_DIR, 'pytradelib.sqlite')
        initialize = self._connect(db_file_path)

        self._sector_columns = OrderedDict([
            ('sector_id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('name', 'TEXT UNIQUE NOT NULL'),
            ])

        self._industry_columns = OrderedDict([
            ('industry_id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('name', 'TEXT UNIQUE NOT NULL'),
            ('sector_id', 'INTEGER REFERENCES sector (sector_id)'),
            ])

        self._symbol_columns = OrderedDict([
            ('symbol_id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('symbol', 'TEXT UNIQUE NOT NULL'),
            ('name', 'TEXT'),
            ('industry_id', 'INTEGER REFERENCES industry (industry_id)'),
            ('exchange', 'TEXT'),
            ('ipo_date', 'TEXT'),
            ('newest_date', 'TEXT'),
            ])

        self._stats_columns = OrderedDict([
            ('symbol_id', 'INTEGER PRIMARY KEY REFERENCES symbol (symbol_id)'),
            ('last_trade_datetime', 'TEXT'),  # delayed ~15mins during market hours
            ('last_trade_price', 'REAL'),     # delayed ~15mins during market hours
            ('last_trade_volume', 'INTEGER'), # delayed ~15mins during market hours
            ('year_high', 'REAL'),
            ('year_low', 'REAL'),
            ('ma_50', 'REAL'),
            ('ma_200', 'REAL'),
            ('market_cap', 'REAL'),
            ('average_daily_volume', 'REAL'), # 3 month
            ('dividend_pay_date', 'TEXT'),
            ('ex_dividend_date', 'TEXT'),
            ('dividend_share', 'REAL'),
            ('dividend_yield', 'REAL'),
            ('book_value', 'REAL'),
            ('ebitda', 'REAL'),
            ('earnings_per_share', 'REAL'),
            ('peg_ratio', 'REAL'),
            ('pe_ratio', 'REAL'),
            ('price_per_book', 'REAL'),
            ('price_per_sales', 'REAL'),
            ('short_ratio', 'REAL'),
            ])

        if initialize:
            self._create_tables()

    def _connect(self, db_file_path):
        self._db_file_path = db_file_path
        initialize = False
        if not os.path.exists(db_file_path):
            utils.mkdir_p(settings.DATA_DIR)
            initialize = True
        self._connection = sqlite3.connect(db_file_path)
        self._connection.text_factory=str # FIXME: use unicode
        return initialize

    def _create_tables(self):
        self.__create_table('sector', self._sector_columns)
        self.__create_table('industry', self._industry_columns)
        self.__create_table('symbol', self._symbol_columns)
        self.__create_table('stats', self._stats_columns)

    def __create_table(self, table_name, column_defs_dict):
        self._connection.execute("CREATE TABLE %s (%s)" % (table_name,
            ','.join([' '.join(c) for c in column_defs_dict.items()])))
        self._connection.commit()

    def _select_row(self, sql, params=None):
        return self._select_rows(sql, params)[0]

    def _select_rows(self, sql, params=None, include_none=True):
        cursor = self._connection.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        # figure out the column names and order of selected results
        sql_columns, junk, select_end = sql[len('SELECT '):].replace(
            ' from ', 'FROM ').replace(' as ', ' AS ').partition(' FROM ')
        if ' * ' in sql:
            table_name = select_end.partition(' ')[0]
            columns = self.__getattribute__('_%s_columns' % table_name).keys()
        else:
            columns = [x.partition(' AS ')[2].strip()
                        if ' AS ' in x else x.strip()
                        for x in sql_columns.split(',')]

        # load the results into a list of dicts and return
        ret = [dict([(x, row[i]) for i, x in enumerate(columns)
                if row[i] or include_none])
                for row in cursor]
        cursor.close()
        return ret

    def _execute_many(self, sql, params_generator):
        cursor = self._connection.cursor()
        cursor.executemany(sql, params_generator())
        self._connection.commit()
        cursor.close()

    @utils.lower
    def _get_symbol_id(self, symbol):
        try:
            sql = "SELECT symbol_id FROM symbol WHERE symbol=?"
            return self._select_row(sql, (symbol,))['symbol_id']
        except IndexError:
            sql = 'INSERT INTO symbol (symbol) VALUES (?)'
            ret = self._connection.execute(sql, (symbol,))
            # FIXME: potential optimization: shouldn't _get_symbol_id always
            # be called by somebody who will commit soon thereafter?
            self._connection.commit()
            return ret.lastrowid

    def _get_sector_id(self, sector):
        sql = "SELECT sector_id FROM sector WHERE name=?"
        return self._select_row(sql, (sector,))['sector_id']

    def _get_industry_id(self, industry):
        sql = "SELECT industry_id FROM industry WHERE name=?"
        return self._select_row(sql, (industry,))['industry_id']

    def insert_or_update_sectors(self, sectors):
        ''' Save sectors to the db.

        :param sectors: A sector name or list of sector names.
        :type sectors: string or list of strings
        '''
        if not isinstance(sectors, list):
            sectors = [sectors]
        self.__insert_or_update('sector', [{'name': s} for s in sectors])

    def insert_or_update_industries(self, industry_sectors):
        ''' Save industries to the db.

        :param industry_sectors: A tuple('industry name', 'sector name') pair or a list of them
        :type industry_sectors: ('industry names', 'sector names') or list[tuples]
        '''
        if not isinstance(industry_sectors, list):
            assert(isinstance(industry_sectors, tuple))
            assert(len(industry_sectors) == 2)
            industry_sectors = [industry_sectors]
        self.__insert_or_update('industry', [
            { 'name': i, 'sector_id': self._get_sector_id(s)}
            for i, s in industry_sectors
            ])

    def insert_or_update_symbols(self, symbol_dicts):
        ''' Save symbols to the db.

        :param symbol_dicts: dict or list of dicts. Required Keys: symbol. Optional: name, industry, exchange, ipo_date, newest_date
        :type symbol_dicts: [{keys: symbol, [any optional keys]}]
        '''
        if not isinstance(symbol_dicts, (list, tuple)):
            assert(isinstance(symbol_dicts, dict))
            symbol_dicts = [symbol_dicts]
        for d in symbol_dicts:
            d['symbol'] = d['symbol'].lower()
            if 'industry' in d:
                d['industry_id'] = self._get_industry_id(d.pop('industry'))
        self.__insert_or_update('symbol', symbol_dicts)

    def insert_or_update_stats(self, stats):
        # some of the keys in stats belong in the symbol table; separate them here.
        symbol_dicts = []
        for d in stats:
            d['symbol'] = d['symbol'].lower()
            new_d = {'symbol': d['symbol']}
            for key in ['name', 'industry', 'exchange']:
                if key in d:
                    new_d[key] = d.pop(key)
            symbol_dicts.append(new_d)
        self.insert_or_update_symbols(symbol_dicts)
        self.__insert_or_update('stats', stats, remove_keys=['sector', 'ipo_date', 'newest_date'])

    def __insert_or_update(self, table_name, list_of_dicts, remove_keys=None):
        if remove_keys:
            for d in list_of_dicts:
                for key in remove_keys:
                    d.pop(key)
        columns = list_of_dicts[0].keys()
        sql = "INSERT OR REPLACE INTO %s (%s) VALUES (%s?)" % ( table_name,
            ','.join(columns), '?,' * (len(columns) - 1))
        def param_gen():
            for d in list_of_dicts:
                yield tuple(v for v in d.values())
        self._execute_many(sql, param_gen)

    def insert_or_update_instruments(self, instruments):
        all_symbols = {}
        for instrument in instruments:
            all_symbols[instrument.symbol()] = {
                'name': instrument.name(),
                'industry': instrument.industry()}
        self.insert_or_update_symbols(all_symbols)

        sql = "INSERT OR REPLACE INTO stats (%s) VALUES (%s?)" % (
                ','.join(self._stats_columns),
                '?,' * (len(self._stats_columns) - 1))
        def param_gen():
            for instrument in instruments:
                keys = self._stats_columns.keys()
                keys.pop(0) # 'symbol_id'
                yield (
                    self._get_symbol_id(instrument.symbol()),
                    #*[instrument[key] for key in keys],
                    instrument['last_trade_datetime'],
                    instrument['last_trade_price'],
                    instrument['last_trade_volume'],
                    instrument['year_high'],
                    instrument['year_low'],
                    instrument['ma_50'],
                    instrument['ma_200'],
                    instrument['market_cap'],
                    instrument['average_daily_volume'],
                    instrument['dividend_pay_date'],
                    instrument['ex_dividend_date'],
                    instrument['dividend_share'],
                    instrument['dividend_yield'],
                    instrument['book_value'],
                    instrument['ebitda'],
                    instrument['earnings_per_share'],
                    instrument['peg_ratio'],
                    instrument['pe_ratio'],
                    instrument['price_per_book'],
                    instrument['price_per_sales'],
                    instrument['short_ratio'],
                    )
        self._execute_many(sql, param_gen)

    def delete_symbol(self, symbol):
        id_ = self._get_symbol_id(symbol)
        delete_sql = [
            "DELETE FROM stats WHERE symbol_id=?"
            "DELETE FROM symbol WHERE symbol_id=?",
            ]
        for sql in delete_sql:
            self._connection.execute(sql, (id_,))
        self._connection.commit()

    def get_symbols(self):
        sql = "SELECT symbol FROM symbol"
        return [row['symbol'] for row in self._select_rows(sql)]

    def get_sectors(self):
        sql = "SELECT name FROM sector"
        return [row['name'] for row in self._select_rows(sql)]

    def get_industries(self):
        sql = "SELECT name FROM industry"
        return [row['name'] for row in self._select_rows(sql)]

    #def get_instrument(self, symbol):
        #sql = "SELECT %s FROM instrument WHERE symbol=?" % (
            #','.join(self._stats_columns)) # ['instrument.%s' % col for col in self._stats_columns]))
        #row = self._select_row(sql, [symbol])
        #ret = dict((self._stats_columns[i], row[i]) for i in xrange(len(row)))
        #return ret

    #def get_instruments(self, symbols):
        #rows = self._select_rows()

        #ret = [ dict((self._stats_columns[i], row[i]) \
            #for i in xrange(len(row))) for row in rows ]
