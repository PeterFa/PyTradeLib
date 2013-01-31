# PyAlgoTrade
# 
# Copyright 2011 Gabriel Martin Becedillas Ruiz
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

import unittest
import datetime

from pyalgotrade import dataseries
from pyalgotrade import bar

class TestSequenceDataSeries(unittest.TestCase):
    def testEmpty(self):
        ds = dataseries.SequenceDataSeries([])
        self.assertTrue(ds.get_first_valid_index() == 0)
        self.assertTrue(ds.get_length() == 0)
        with self.assertRaises(IndexError):
            ds[-1]
        with self.assertRaises(IndexError):
            ds[-2]
        with self.assertRaises(IndexError):
            ds[0]
        with self.assertRaises(IndexError):
            ds[1]

    def testNonEmpty(self):
        ds = dataseries.SequenceDataSeries(range(10))
        self.assertTrue(ds.get_first_valid_index() == 0)
        self.assertTrue(ds.get_length() == 10)
        self.assertTrue(ds[-1] == 9)
        self.assertTrue(ds[-2] == 8)
        self.assertTrue(ds[0] == 0)
        self.assertTrue(ds[1] == 1)

        self.assertTrue(ds.get_values(1) == [9])
        self.assertTrue(ds.get_values(2) == [8, 9])
        self.assertTrue(ds.get_values(1, 1) == [8])
        self.assertTrue(ds.get_values(2, 1) == [7, 8])

        self.assertTrue(ds.get_values_absolute(1, 3) == [1, 2, 3])
        self.assertTrue(ds.get_values_absolute(9, 9) == [9])
        self.assertTrue(ds.get_values_absolute(9, 10) == None)
        self.assertTrue(ds.get_values_absolute(9, 10, True) == [9, None])

    def testSeqLikeOps(self):
        seq = range(10)
        ds = dataseries.SequenceDataSeries(seq)

        # Test length and every item.
        self.assertEqual(len(ds), len(seq))
        for i in xrange(len(seq)):
            self.assertEqual(ds[i], seq[i])

        # Test negative indices
        self.assertEqual(ds[-1], seq[-1])
        self.assertEqual(ds[-2], seq[-2])
        self.assertEqual(ds[-9], seq[-9])

        # Test slices
        sl = slice(0,1,2)
        self.assertEqual(ds[sl], seq[sl])
        sl = slice(0,9,2)
        self.assertEqual(ds[sl], seq[sl])
        sl = slice(0,-1,1)
        self.assertEqual(ds[sl], seq[sl])

        for i in xrange(-100, 100):
            self.assertEqual(ds[i:], seq[i:])

        for step in xrange(1, 10):
            for i in xrange(-100, 100):
                self.assertEqual(ds[i::step], seq[i::step])

class TestBarDataSeries(unittest.TestCase):
    def testEmpty(self):
        ds = dataseries.BarDataSeries()
        self.assertTrue(ds.get_value(-2) == None)
        self.assertTrue(ds.get_value(-1) == None)
        self.assertTrue(ds.get_value() == None)
        self.assertTrue(ds.get_value(1) == None)
        self.assertTrue(ds.get_value(2) == None)

        with self.assertRaises(IndexError):
            ds[-1]
        with self.assertRaises(IndexError):
            ds[0]
        with self.assertRaises(IndexError):
            ds[1000]

    def testAppendInvalidDatetime(self):
        ds = dataseries.BarDataSeries()
        for i in range(10):
            now = datetime.datetime.now() + datetime.timedelta(seconds=i)
            ds.append_value( bar.Bar(now, 0, 0, 0, 0, 0, 0) )
            # Adding the same datetime twice should fail
            self.assertRaises(Exception, ds.append_value, bar.Bar(now, 0, 0, 0, 0, 0, 0))
            # Adding a previous datetime should fail
            self.assertRaises(Exception, ds.append_value, bar.Bar(now - datetime.timedelta(seconds=i), 0, 0, 0, 0, 0, 0))

    def testNonEmpty(self):
        ds = dataseries.BarDataSeries()
        for i in range(10):
            ds.append_value( bar.Bar(datetime.datetime.now() + datetime.timedelta(seconds=i), 0, 0, 0, 0, 0, 0) )

        for i in range(0, 10):
            self.assertTrue(ds.get_value(i) != None)

    def __testGetValue(self, ds, itemCount, value):
        for i in range(0, itemCount):
            self.assertTrue(ds.get_value(i) == value)

    def testNestedDataSeries(self):
        ds = dataseries.BarDataSeries()
        for i in range(10):
            ds.append_value( bar.Bar(datetime.datetime.now() + datetime.timedelta(seconds=i), 2, 4, 1, 3, 10, 3) )

        self.__testGetValue(ds.get_open_data_series(), 10, 2)
        self.__testGetValue(ds.get_close_data_series(), 10, 3)
        self.__testGetValue(ds.get_high_data_series(), 10, 4)
        self.__testGetValue(ds.get_low_data_series(), 10, 1)
        self.__testGetValue(ds.get_volume_data_series(), 10, 10)
        self.__testGetValue(ds.get_adj_close_data_series(), 10, 3)

    def testSeqLikeOps(self):
        ds = dataseries.BarDataSeries()
        for i in range(10):
            ds.append_value( bar.Bar(datetime.datetime.now() + datetime.timedelta(seconds=i), 2, 4, 1, 3, 10, 3) )

        self.assertEqual(ds[-1], ds.get_value())
        self.assertEqual(ds[-2], ds.get_value(1))
        self.assertEqual(ds[0], ds[0])
        self.assertEqual(ds[1], ds[1])
        self.assertEqual(ds[-2:][-1], ds.get_value())

def getTestCases():
    ret = []

    ret.append(TestSequenceDataSeries("testEmpty"))
    ret.append(TestSequenceDataSeries("testNonEmpty"))
    ret.append(TestSequenceDataSeries("testSeqLikeOps"))

    ret.append(TestBarDataSeries("testEmpty"))
    ret.append(TestBarDataSeries("testAppendInvalidDatetime"))
    ret.append(TestBarDataSeries("testNonEmpty"))
    ret.append(TestBarDataSeries("testNestedDataSeries"))
    ret.append(TestBarDataSeries("testSeqLikeOps"))
    return ret

