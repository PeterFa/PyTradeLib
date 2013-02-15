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
import pytz
import datetime

LOCAL_TIMEZONE = pytz.timezone('America/New_York')
DATE_FORMAT = '%Y-%m-%d %H:%M:%S' # YYYY-MM-DD HH:MM:SS

DATA_DIR = os.path.join(os.environ['HOME'], 'pytradelib_data')
DATA_PROVIDER = 'Yahoo'
DATA_STORE_FORMAT = 'Yahoo'
DATA_COMPRESSION = None # 'lz4', 'gz', or None (for uncompressed csv)

SYMBOL_INDEX_PATH = os.path.join(DATA_DIR, 'symbol_index.json')
FAILED_SYMBOLS_PATH = os.path.join(DATA_DIR, 'failed_symbols.json')
DATA_LAST_UPDATED_PATH = os.path.join(DATA_DIR, '.last_updated_times.json')
