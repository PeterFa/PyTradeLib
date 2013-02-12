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

import gevent.monkey
gevent.monkey.patch_socket()

import os
import errno
import time
import urllib2
import gevent
from decorator import decorator

try: import simplejson as json
except: import json
try: import cPickle as pickle
except: import pickle

from pytradelab import settings

## --- string utils ---------------------------------------------------------
@decorator
def lower(fn, obj, string, *args, **kwargs):
    return fn(obj, string.lower(), *args, **kwargs)

def try_dict_str_values_to_float(dict_):
    # try to convert remaining strings to float
    for key, value in dict_.items():
        if isinstance(value, str):
            # first assume the value is a quoted number
            try:
                if '.' in value:
                    dict_[key] = float(value)
                else:
                    dict_[key] = int(value)
            except ValueError:
                # then assume the value is a large number suffixed with K/M/B/T
                try:
                    dict_[key] = convert_KMBT_str_to_int(value)
                # otherwise just leave the value as a string
                except ValueError:
                    pass
    return dict_

def convert_KMBT_str_to_int(value):
    def to_float(value):
        return float(value[:-1])
    if value.endswith('K'):
        value = to_float(value) * 1000
    elif value.endswith('M'):
        value = to_float(value) * 1000000
    elif value.endswith('B'):
        value = to_float(value) * 1000000000
    elif value.endswith('T'):
        value = to_float(value) * 1000000000000
    else:
        raise ValueError
    return int(value)


## --- file utils ---------------------------------------------------------
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise e

def get_extension(compression_type):
    if settings.DATA_COMPRESSION == None:
        extension = 'csv'
    elif settings.DATA_COMPRESSION == 'lz4':
        extension = 'csv.lz4'
    elif settings.DATA_COMPRESSION == 'gz':
        extension = 'csv.gz'
    return extension

def supports_seeking(compression_type):
    if compression_type in [None, 'gz']:
        return True
    return False

def slug(string):
    return string.lower().replace(' ', '_').replace('&', 'and')

def save_to_json(data, file_path):
    with open(file_path, 'w') as f:
        f.write(json.dumps(data))

def load_from_json(file_path):
    with open(file_path, 'r') as f:
        return json.loads(f.read())

def save_to_pickle(data, file_path):
    with open(file_path, 'w') as f:
        f.write(pickle.dumps(data))

def load_from_pickle(file_path):
    with open(file_path, 'r') as f:
        return pickle.loads(f.read())


## --- multiprocessing/threading/gevent utils ------------------------------
def batch(list_, size=100, sleep=None):
    total_batches = len(list_)/size + 1
    for i in xrange(total_batches):
        lowerIdx = size * i
        upperIdx = size * (i+1)
        if upperIdx <= len(list_):
            yield list_[lowerIdx:upperIdx]
        else:
            yield list_[lowerIdx:]

        if sleep and upperIdx < len(list_):
            time.sleep(sleep)


## --- downloading utils ---------------------------------------------------
def download(url, tag=None):
    tag = tag or url
    tag = {'tag': tag}
    
    # try downloading the url; return on success, retry on various URLErrors and
    #  (gracefully) fail on HTTP 404 errors. unrecognized exceptions still get raised.
    while True:
        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            if '404' in str(e):
                tag['error'] = str(e)
                return (None, tag)
            else:
                raise e
        except urllib2.URLError, e:
            if 'server failed' in str(e) or 'misformatted query' in str(e):
                time.sleep(0.02)
                print 'retrying download of %s' % url
            elif 'connection reset by peer' in str(e) or 'request timed out' in str(e):
                time.sleep(0.2)
                print 'retrying download of %s' % url
            else:
                raise e
        else:
            data = response.read()
            return (data, tag)

def bulk_download(urls_andor_tags_list):
    '''
    :type urls_andor_tags_list: a list of urls or a list of tuple(url, tag)s
    '''
    threads = []
    for params in urls_andor_tags_list:
        if isinstance(params, tuple):
            threads.append(gevent.spawn(download, *params))
        else:
            threads.append(gevent.spawn(download, params))
    gevent.joinall(threads)
    for thread in threads:
        yield thread.value
