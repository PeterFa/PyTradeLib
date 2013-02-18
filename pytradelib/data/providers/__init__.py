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
import importlib


class ProviderFactory(object):
    def __init__(self):
        self.__supported = []
        self.__cache = {}

    def get_supported_data_providers(self):
        if not self.__supported:
            dir_ = os.path.join(os.path.dirname(__file__))
            for provider in os.listdir(dir_):
                if os.path.isdir(os.path.join(dir_, provider)):
                    self.__supported.append(provider)
        return self.__supported

    def get_data_provider(self, name):
        name = name.lower()
        if name not in self.__cache:
            if name not in self.get_supported_data_providers():
                raise NotImplementedError('"%s" is not supported.' % name)
            provider_module = importlib.import_module(
                '.'.join(['pytradelib', 'data', 'providers', name]))
            self.__cache[name] = provider_module.Provider()
        return self.__cache[name]

ProviderFactory = ProviderFactory()
