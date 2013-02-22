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

try: import simplejson as json
except: import json

from pytradelib import utils
from pytradelib.data import db
from pytradelib.data import providers
from pytradelib.failed import Symbols as FailedSymbols


class YQLMixin(object):
    def name(self, suffix=None):
        return 'YahooYQL' + suffix if suffix else 'YahooYQL'

    def _get_yql_url(self, yql):
        base_url = 'http://query.yahooapis.com/v1/public/yql'
        query = urllib.urlencode({
            'q': yql,
            'env': 'store://datatables.org/alltableswithkeys',
            'format': 'json' })
        return ''.join([base_url, '?', query])

    def _load_and_verify_data(self, data, context):
        data = json.loads(data)
        if data and isinstance(data, dict):
            if 'error' in data:
                raise Exception('Query failed for %s: %s' % (
                    context['yql'], data['error']['description']))
            if 'query' in data:
                query = data['query']
                if query and 'results' in query:
                    results = query['results']
                    if results and context['validate_field'] in results:
                        return results[context['validate_field']]
                    else:
                        raise Exception(
                            'got results for "%s" but none valid:\n%s' % (
                            context['yql'], data))
                else:
                    raise Exception('no results for "%s":\n%s' % (
                                    context['yql'], data))
            else:
                raise Exception('"query" not in "%s":\n%s' % (
                                context['yql'], data))
        else:
            raise Exception('invalid data returned for "%s":\n%s' % (
                            context['yql'], data))

    def verify_download(self, data_context):
        for raw_data, context in data_context:
            if 'error' not in context or not context['error']:
                data = self._load_and_verify_data(raw_data, context)
                if data:
                    if not isinstance(data, list):
                        data = [data]
                    yield data, context
            else:
                print 'Error downloading stats for symbols in %s: %s' % (
                    context['url'], context['error'])

    def convert_data(self, data_contexts, other_provider=None):
        for data_context in data_contexts:
            yield data_context

    def update_data(self, data_contexts):
        for data_context in data_contexts:
            yield data_context


class Sectors(YQLMixin, providers.Provider):
    def __init__(self):
        self._db = db.Database()

    @property
    def name(self):
        return YQLMixin.name(self, 'Sectors')

    def get_url(self, context=None):
        context = context or {}
        yql = 'select * from yahoo.finance.sectors'
        context['validate_field'] = 'sector'
        context['yql'] = yql
        url = self._get_yql_url(yql)
        return url, context

    def get_urls(self, context=None):
        return [self.get_url(context)]

    def verify_download(self, data_context):
        for data, context in YQLMixin.verify_download(self, data_context):
            for sector in data:
                yield sector, context

    def process_downloaded_data(self, sector_contexts):
        ret = {'sectors': [], 'industries': []}
        for sector, context in sector_contexts:
            ret['sectors'].append(sector['name'])
            industries = sector['industry']
            if not isinstance(industries, list):
                industries = [industries]
            for industry in industries:
                ret['industries'].append({'name': industry['name'],
                                          'yahoo_id': industry['id'],
                                          'sector': sector['name']})
        yield ret, context

    def save_data(self, data_context):
        data, context = [x for x in data_context][0]
        self._db.insert_or_update_sectors(data['sectors'])
        self._db.insert_or_update_industries(data['industries'])
        yield context


class Industries(YQLMixin, providers.Provider):
    def __init__(self):
        self._db = db.Database()

    @property
    def name(self):
        return YQLMixin.name(self, 'Industries')

    def get_url(self, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        context = context or {}
        yql = 'select * from yahoo.finance.industry where id in (%s)' % ','.join(
                ['"%s"' % i for i in ids])
        context['validate_field'] = 'industry'
        context['yql'] = yql
        url = self._get_yql_url(yql)
        return url, context

    def get_urls(self, ids, context=None):
        return [self.get_url(x, context) for x in utils.batch(ids, size=10)]

    def verify_download(self, data_context):
        for data, context in YQLMixin.verify_download(self, data_context):
            for industry in data:
                yield industry, context

    def process_downloaded_data(self, industry_contexts):
        for industry, context in industry_contexts:
            if 'company' in industry:
                for instrument in industry['company']:
                    if isinstance(instrument, dict):
                        symbol = {
                            'symbol': instrument['symbol'].lower(),
                            'name': instrument['name'].encode('utf-8'),
                            'industry': industry['name'],
                            }
                        yield symbol, context

    def save_data(self, symbol_contexts):
        symbols = [x for x, context in symbol_contexts]
        self._db.insert_or_update_symbols(symbols)
        yield context


def update_sectors_and_industries():
    _db = db.Database()
    _downloader = Sectors()
    urls = _downloader.get_urls()
    sectors_and_industries = \
        _downloader.process_downloaded_data(
            _downloader.verify_download(
                utils.bulk_download(urls)))
    final_context = [x for x in _downloader.save_data(sectors_and_industries)][0]

def update_symbol_index():
    _db = db.Database()
    _downloader = Industries()
    ids = _db.get_industry_ids()
    urls = _downloader.get_urls(ids)
    symbols = \
        _downloader.process_downloaded_data(
            _downloader.verify_download(
                utils.bulk_download(urls)))
    final_context = [x for x in _downloader.save_data(symbols)][0]

def update_index():
    update_sectors_and_industries()
    update_symbol_index()

if __name__ == '__main__':
    update_index()
