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

import os

from pytradelab import utils
from pytradelab import settings

class Symbols(object):
    def __init__(self):
        self.__dict = {}
        self.__blacklisted = []
        self.load()

    def load(self):
        if os.path.exists(settings.FAILED_SYMBOLS_PATH):
            d = utils.load_from_json(settings.FAILED_SYMBOLS_PATH)
            self.__dict = d['errors']
            self.__blacklisted = d['blacklisted']

    def save(self):
        d = {'errors': self.__dict, 'blacklisted': self.__blacklisted}
        utils.save_to_json(d, settings.FAILED_SYMBOLS_PATH)

    def get_symbols(self):
        return self.__dict.keys()

    @utils.lower
    def __contains__(self, symbol):
        if symbol in self.__dict:
            return True
        return False

    @utils.lower
    def get_error(self, symbol):
        if symbol in self.__dict:
            return self.__dict[symbol]
        return None

    def get_failed_symbols(self):
        symbols = [x for x in self.__dict if x not in self.__blacklisted]
        return symbols

    def get_blacklisted_symbols(self):
        return self.__blacklisted

    def get_failed_errors(self):
        ret = dict((x, self.__dict[x]) for x in self.get_failed_symbols())
        return ret

    def get_blacklisted_errors(self):
        ret = dict((x, self.__dict[x]) for x in self.get_blacklisted_symbols())
        return ret

    @utils.lower
    def add_failed(self, symbol, reason_failed_msg):
        print 'adding failed symbol: %s: %s' % (symbol, reason_failed_msg)
        self.__dict[symbol] = reason_failed_msg
        self.save()

    @utils.lower
    def add_blacklisted(self, symbol, reason_blacklisted_msg=None):
        print 'adding blacklisted symbol: %s: %s' % (symbol, reason_blacklisted_msg)
        self.__dict[symbol] = reason_blacklisted_msg
        self.__blacklisted.append(symbol)
        self.save()

    @utils.lower
    def remove_failed(self, symbol):
        print 'removing failed symbol: %s' % symbol
        reason_added = self.__dict.pop(symbol)
        self.save()
        return reason_added

    @utils.lower
    def remove_blacklisted(self, symbol):
        print 'removing blacklisted symbol: %s' % symbol
        self.__blacklisted.pop(self.__blacklisted.index(symbol))
        reason_added = self.__dict.pop(symbol)
        self.save()
        return reason_added

Symbols = Symbols()
