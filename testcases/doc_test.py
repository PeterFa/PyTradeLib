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

import unittest
import subprocess
import os
import shutil

def run_and_get_output(cmd):
    return subprocess.check_output(cmd, universal_newlines=True)

def run_python_code(code, outputFileName=None):
    cmd = ["python"]
    cmd.append("-u")
    cmd.append("-c")
    cmd.append(code)
    ret = run_and_get_output(cmd)
    if outputFileName:
        outputFile = open(outputFileName, "w")
        outputFile.write(ret)
        outputFile.close()
    return ret

def run_python_script(script, params=[]):
    cmd = ["python"]
    cmd.append(script)
    cmd.extend(params)
    return run_and_get_output(cmd)

def run_sample_script(script, params=[]):
    return run_python_script(os.path.join("samples", script), params)

def get_file_lines(fileName):
    rawLines = open(fileName, "r").readlines()
    return [rawLine.strip() for rawLine in rawLines]

def compare_head(fileName, lines):
    assert(len(lines) > 0)
    fileLines = get_file_lines(os.path.join("samples", fileName))
    return fileLines[0:len(lines)] == lines 

def compare_tail(fileName, lines):
    assert(len(lines) > 0)
    fileLines = get_file_lines(os.path.join("samples", fileName))
    return fileLines[len(lines)*-1:] == lines 

class TutorialTestCase(unittest.TestCase):
    def testTutorial1(self):
        run_python_code("from pytradelib.deprecated import yahoofinance; print yahoofinance.get_daily_csv('orcl', 2000)", "orcl-2000.csv")
        lines = run_sample_script("tutorial-1.py").split("\n")
        self.assertTrue(compare_head("tutorial-1.output", lines[:3]))
        self.assertTrue(compare_tail("tutorial-1.output", lines[-4:-1]))

    def testTutorial2(self):
        # run_python_code("from pytradelib.deprecated import yahoofinance; print yahoofinance.get_daily_csv('orcl', 2000)", "orcl-2000.csv")
        lines = run_sample_script("tutorial-2.py").split("\n")
        self.assertTrue(compare_head("tutorial-2.output", lines[:15]))
        self.assertTrue(compare_tail("tutorial-2.output", lines[-4:-1]))

    def testTutorial3(self):
        # run_python_code("from pytradelib.deprecated import yahoofinance; print yahoofinance.get_daily_csv('orcl', 2000)", "orcl-2000.csv")
        lines = run_sample_script("tutorial-3.py").split("\n")
        self.assertTrue(compare_head("tutorial-3.output", lines[:30]))
        self.assertTrue(compare_tail("tutorial-3.output", lines[-4:-1]))

    def testTutorial4(self):
        # run_python_code("from pytradelib.deprecated import yahoofinance; print yahoofinance.get_daily_csv('orcl', 2000)", "orcl-2000.csv")
        lines = run_sample_script("tutorial-4.py").split("\n")
        self.assertTrue(compare_head("tutorial-4.output", lines[:-1]))

class CompInvTestCase(unittest.TestCase):
    def testCompInv_1(self):
        shutil.copy2(os.path.join("samples", "aeti-2011-yahoofinance.csv"), ".")
        shutil.copy2(os.path.join("samples", "egan-2011-yahoofinance.csv"), ".")
        shutil.copy2(os.path.join("samples", "simo-2011-yahoofinance.csv"), ".")
        shutil.copy2(os.path.join("samples", "glng-2011-yahoofinance.csv"), ".")
        lines = run_sample_script("compinv-1.py").split("\n")
        self.assertTrue(compare_head("compinv-1.output", lines[:-1]))

class DataSeriesTestCase(unittest.TestCase):
    def testDataSeries_1(self):
        lines = run_sample_script("dataseries-1.py").split("\n")
        self.assertTrue(compare_head("dataseries-1.output", lines[:-1]))

class StratAnalyzerTestCase(unittest.TestCase):
    def testSampleStrategyAnalyzer(self):
        lines = run_sample_script("sample-strategy-analyzer.py").split("\n")
        self.assertTrue(compare_head("sample-strategy-analyzer.output", lines[:-1]))

class TechnicalTestCase(unittest.TestCase):
    def testTechnical_1(self):
        lines = run_sample_script("technical-1.py").split("\n")
        self.assertTrue(compare_head("technical-1.output", lines[:-1]))


def getTestCases():
    ret = []
    ret.append(TutorialTestCase("testTutorial1"))
    #ret.append(TutorialTestCase("testTutorial2"))
    #ret.append(TutorialTestCase("testTutorial3"))
    #ret.append(TutorialTestCase("testTutorial4"))
    ret.append(CompInvTestCase("testCompInv_1"))
    ret.append(DataSeriesTestCase("testDataSeries_1"))
    #ret.append(StratAnalyzerTestCase("testSampleStrategyAnalyzer"))
    #ret.append(TechnicalTestCase("testTechnical_1"))
    return ret
