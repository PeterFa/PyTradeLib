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
import abc
import importlib

from pytradelib import utils
from pytradelib import settings


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


class Provider(object):
    '''The base class data providers should subclass.
    '''
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def name(self):
        return

    @abc.abstractmethod
    def get_url(self, symbol, context):
        return

    @abc.abstractmethod
    def get_urls(self, symbol_contexts):
        yield

    @abc.abstractmethod
    def verify_download(self, data_contexts):
        yield

    @abc.abstractmethod
    def process_downloaded_data(self, data_contexts):
        yield

    @abc.abstractmethod
    def convert_data(self, data_contexts, other_provider):
        yield

    @abc.abstractmethod
    def update_data(self, data_contexts):
        yield

    @abc.abstractmethod
    def save_data(self, data_contexts):
        yield


class OpenFilesMixin(object):
    def __yield_open_files(self, data_contexts, mode):
        '''
        :param tag_file_paths: tuple(anything, file_path_to_open)
        :param mode: any mode supported by the selected compression backend
        '''
        for data, context in data_contexts:
            file_path = context['file_path']
            if mode == 'w':
                utils.mkdir_p(os.path.dirname(file_path))
            compression = settings.DATA_COMPRESSION
            if compression == 'gz':
                f = gzip.open(file_path, mode)
            elif not compression or compression == 'lz4':
                f = open(file_path, mode)
            context['_open_file'] = f
            yield data, context

    def open_files_readable(self, data_contexts):
        for data_context in self.__yield_open_files(data_contexts, 'r'):
            yield data_context

    def open_files_writeable(self, data_contexts):
        for data_context in self.__yield_open_files(data_contexts, 'w'):
            yield data_context

    def open_files_updatable(self, data_contexts):
        for data_context in self.__yield_open_files(data_contexts, 'r+'):
            yield data_context


    def symbol_rows(symbol_files):
        for symbol, f in symbol_files:
            data = f.read()
            f.close()
            if settings.DATA_COMPRESSION == 'lz4':
                data = lz4.loads(data)

            # split the file into rows, slicing off the header labels
            csv_rows = data.strip().split('\n')[1:]
            yield (symbol, csv_rows)
