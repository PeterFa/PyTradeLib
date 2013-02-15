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
import datetime

from collections import OrderedDict

from pytradelib import utils
from pytradelib import settings


class BaseDatabase(object):
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
            ])

        self._stats_columns = OrderedDict([
            ('symbol_id', 'INTEGER PRIMARY KEY REFERENCES symbol (symbol_id)'),
            ('last_trade_datetime', 'TEXT'),  # delayed ~15mins during mkt hrs
            ('last_trade_price', 'REAL'),     # delayed ~15mins during mkt hrs
            ('last_trade_volume', 'INTEGER'), # delayed ~15mins during mkt hrs
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

        self._system_last_updated_columns = OrderedDict([
            ('update_id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('symbol_index', 'TEXT'),
            ])

        self._symbol_last_updated_columns = OrderedDict([
            ('symbol_id', 'INTEGER PRIMARY KEY REFERENCES symbol (symbol_id)'),
            ('stats', 'TEXT'),
            ('minute', 'TEXT'),
            ('day', 'TEXT'),
            ('week', 'TEXT'),
            ('month', 'TEXT'),
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
        self.__create_table('system_last_updated',
                                            self._system_last_updated_columns)
        self.__create_table('symbol_last_updated',
                                            self._symbol_last_updated_columns)

    def __create_table(self, table_name, column_defs_dict):
        self._connection.execute("CREATE TABLE %s (%s)" % (table_name,
            ','.join([' '.join(x) for x in column_defs_dict.items()])))
        self._connection.commit()

    def select_row(self, sql, params=None):
        rows = self.select_rows(sql, params)
        return rows[0] if rows else None

    def select_rows(self, sql, params=None, include_none=True):
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

    def insert_or_update(self, table_name, list_of_dicts, remove_keys=None):
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
        self.execute_many(sql, param_gen)

    def execute_many(self, sql, params_generator):
        cursor = self._connection.cursor()
        cursor.executemany(sql, params_generator())
        self._connection.commit()
        cursor.close()

    @utils.lower
    def get_symbol_id(self, symbol):
        try:
            sql = "SELECT symbol_id FROM symbol WHERE symbol=?"
            return self.select_row(sql, (symbol,))['symbol_id']
        except TypeError:
            sql = 'INSERT INTO symbol (symbol) VALUES (?)'
            ret = self._connection.execute(sql, (symbol,))
            # FIXME: potential optimization: shouldn't get_symbol_id() always
            # be called by somebody who will commit soon thereafter?
            self._connection.commit()
            return ret.lastrowid

    def get_sector_id(self, sector):
        sql = "SELECT sector_id FROM sector WHERE name=?"
        return self.select_row(sql, (sector,))['sector_id']

    def get_industry_id(self, industry):
        sql = "SELECT industry_id FROM industry WHERE name=?"
        return self.select_row(sql, (industry,))['industry_id']

    @utils.lower
    def delete_symbol(self, symbol):
        id_ = self.get_symbol_id(symbol)
        delete_sql = [
            "DELETE FROM stats WHERE symbol_id=?"
            "DELETE FROM symbol WHERE symbol_id=?",
            ]
        for sql in delete_sql:
            self._connection.execute(sql, (id_,))
        self._connection.commit()


class Database(object):
    def __init__(self, db_file_path=None):
        self._db = BaseDatabase(db_file_path)

    @property
    def sector_columns(self):
        return self._db._sector_columns.keys()

    @property
    def industry_columns(self):
        return self._db._industry_columns.keys()

    @property
    def symbol_columns(self):
        return self._db._symbol_columns.keys()

    @property
    def stats_columns(self):
        return self._db._stats_columns.keys()

    @property
    def system_last_updated_columns(self):
        return self._db._system_last_updated_columns.keys()

    @property
    def symbol_last_updated_columns(self):
        return self._db._symbol_last_updated_columns.keys()

    @utils.lower
    def get_symbol_id(self, symbol):
        return self._db.get_symbol_id(symbol)

    def get_sector_id(self, sector):
        return self._db.get_sector_id(sector)

    def get_industry_id(self, industry):
        return self._db.get_industry_id(industry)

    def get_symbols(self):
        sql = "SELECT symbol FROM symbol"
        return [row['symbol'] for row in self._db.select_rows(sql)]

    def get_sectors(self):
        sql = "SELECT name FROM sector"
        return [row['name'] for row in self._db.select_rows(sql)]

    def get_industries(self):
        sql = "SELECT name FROM industry"
        return [row['name'] for row in self._db.select_rows(sql)]

    def get_index(self):
        sql = 'SELECT industry.name AS industry, sector.name AS sector FROM '\
            'industry JOIN sector ON (industry.sector_id = sector.sector_id)'
        ret = {
            'sectors': self.get_sectors(),
            'industry_sectors': [(x['industry'], x['sector'])
                                for x in self._db.select_rows(sql)]
            }
        sql = 'SELECT symbol, symbol.name AS name, sector.name AS sector, '\
            'industry.name AS industry FROM symbol '\
            'JOIN industry ON (symbol.industry_id = industry.industry_id) '\
            'JOIN sector ON (industry.sector_id = sector.sector_id)'
        ret['symbols'] = self._db.select_rows(sql)
        return ret

    def get_updated(self, what, symbol=None):
        sql = 'SELECT %s FROM ' % what
        if what in self.system_last_updated_columns:
            sql += 'system_last_updated'
            row = self._db.select_row(sql)
        else:
            if symbol is None:
                raise Exception('must provide the symbol with "%s"' % what)
            sql += 'symbol_last_updated WHERE symbol_id=?'
            row = self._db.select_row(sql, (self.get_symbol_id(symbol),))
        return datetime.datetime.strptime(row[what], '%Y-%m-%d %H:%M:%S')\
            if row else None

    def set_updated(self, what, symbol=None, when=None):
        if not when:
            when = datetime.datetime.now() # FIXME: use UTC
        when = when.strftime('%Y-%m-%d %H:%M:%S')
        if what in self.system_last_updated_columns:
            self._db.insert_or_update('system_last_updated', [{what: when}])
        else:
            if symbol is None:
                raise Exception('must provide the symbol with "%s"' % what)
            self._db.insert_or_update('symbol_last_updated',
                [{'symbol_id': self._db.get_symbol_id(symbol), what: when}])

    def insert_or_update_sectors(self, sectors):
        ''' Save sectors to the db.

        :param sectors: A sector name or list of sector names.
        :type sectors: string or list of strings
        '''
        if not isinstance(sectors, list):
            sectors = [sectors]
        self._db.insert_or_update('sector', [{'name': s} for s in sectors])

    def insert_or_update_industries(self, industry_sectors):
        ''' Save industries to the db.

        :param industry_sectors: [list of] tuple('industry name', 'sector name')
        :type industry_sectors: [list of] tuple('industry name', 'sector name')
        '''
        if not isinstance(industry_sectors, list):
            assert(isinstance(industry_sectors, tuple))
            assert(len(industry_sectors) == 2)
            industry_sectors = [industry_sectors]
        self._db.insert_or_update( 'industry', [
            {'name': x, 'sector_id': self._db.get_sector_id(y)}
            for x, y in industry_sectors
            ])

    def insert_or_update_symbols(self, symbol_dicts):
        ''' Save symbols to the db.

        :param symbol_dicts: Keys: symbol, name, industry, exchange, ipo_date
        :type symbol_dicts: [list of] dict(keys: symbol, [any optional keys])
        '''
        if not isinstance(symbol_dicts, (list, tuple)):
            assert(isinstance(symbol_dicts, dict))
            symbol_dicts = [symbol_dicts]
        for d in symbol_dicts:
            d['symbol'] = d['symbol'].lower()
            if 'industry' in d:
                d['industry_id'] = self._db.get_industry_id(d.pop('industry'))
        self._db.insert_or_update('symbol', symbol_dicts)

    def insert_or_update_stats(self, stats):
        # some of the keys in stats belong in the symbol table; separate them
        symbol_dicts = []
        for d in stats:
            d['symbol'] = d['symbol'].lower()
            new_d = {'symbol': d['symbol']}
            for key in ['name', 'industry', 'exchange']:
                if key in d:
                    new_d[key] = d.pop(key)
            symbol_dicts.append(new_d)
        self.insert_or_update_symbols(symbol_dicts)
        self._db.insert_or_update('stats', stats)

    def insert_or_update_instruments(self, instruments):
        all_symbols = {}
        for instrument in instruments:
            all_symbols[instrument.symbol()] = {
                'name': instrument.name(),
                'industry': instrument.industry()}
        self.insert_or_update_symbols(all_symbols)

        sql = "INSERT OR REPLACE INTO stats (%s) VALUES (%s?)" % (
                ','.join(self.stats_columns),
                '?,' * (len(self.stats_columns) - 1))
        def param_gen():
            for instrument in instruments:
                params = [self.get_symbol_id(instrument.symbol())]
                keys = self.stats_columns
                keys.pop(0) # 'symbol_id'
                params.extend([instrument[key] for key in keys])
                yield tuple(params)
        self._db.execute_many(sql, param_gen)

    @utils.lower
    def delete_symbol(self, symbol):
        self._db.delete_symbol(symbol)

    #def get_instrument(self, symbol):
        #sql = "SELECT %s FROM instrument WHERE symbol=?" % (
            #','.join(self.stats_columns)) # ['instrument.%s' % col for col in self.stats_columns]))
        #row = self._db.select_row(sql, [symbol])
        #ret = dict((self.stats_columns[i], row[i]) for i in xrange(len(row)))
        #return ret

    #def get_instruments(self, symbols):
        #rows = self._db.select_rows()

        #ret = [ dict((self.stats_columns[i], row[i]) \
            #for i in xrange(len(row))) for row in rows ]
