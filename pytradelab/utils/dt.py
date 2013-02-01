# This file was originally part of PyAlgoTrade.
#
# Copyright 2012 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

import datetime
import calendar
import pytz

def datetime_is_naive(date_time):
    """ Returns True if date_time is naive."""
    return date_time.tzinfo is None or date_time.tzinfo.utcoffset(date_time) is None

def localize(date_time, timeZone):
    """Returns a datetime adjusted to a timezone:

    * If date_time is a naive datetime (datetime with no timezone information), timezone information is added but date and time remains the same.
    * If date_time is not a naive datetime, a datetime object with new tzinfo attribute is returned, adjusting the date and time data so the result is the same UTC time.
    """

    if datetime_is_naive(date_time):
        ret = timeZone.localize(date_time)
    else:
        ret = date_time.astimezone(timeZone)
    return ret

def datetime_to_timestamp(date_time):
    """ Converts a datetime.datetime to a UTC timestamp."""
    return calendar.timegm(date_time.utctimetuple())

def timestamp_to_datetime(time_stamp):
    """ Converts a UTC timestamp to a datetime.datetime."""
    ret = datetime.datetime.utcfromtimestamp(time_stamp)
    return localize(ret, pytz.utc)
