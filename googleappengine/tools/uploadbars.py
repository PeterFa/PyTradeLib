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

from optparse import OptionParser
import sys
import os
import tempfile
import hashlib
import subprocess

# Just in case pytradelab isn't installed.
upload_barsPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(upload_barsPath, "..", ".."))

from pytradelab import barfeed
from pytradelab.barfeed import csvfeed


def get_md5(value):
    m = hashlib.md5()
    m.update(value)
    return m.hexdigest()

def datetimeToCSV(date_time):
    return date_time.strftime("%Y-%m-%dT%H:%M:%S")

def parse_cmdline():
    usage = "usage: %prog [options] csv1 csv2 ..."
    parser = OptionParser(usage=usage)
    parser.add_option("-i", "--symbol", dest="symbol", help="Mandatory. The symbol's symbol. Note that all csv files must belong to the same symbol.")
    parser.add_option("-u", "--url", dest="url", help="The location of the remote_api endpoint. Example: http://YOURAPPID.appspot.com/remote_api")
    parser.add_option("-c", "--appcfg_path", dest="appcfg_path", help="Path where appcfg.py resides")
    mandatory_options = [
        "symbol",
        "url",
            ]

    (options, args) = parser.parse_args()

    # Check that all mandatory options are available.
    for opt in mandatory_options:
        if getattr(options, opt) == None:
            raise Exception("--%s option is missing" % opt)

    if len(args) == 0:
        raise Exception("No csv files to upload")

    return (options, args)

def gen_bar_key(symbol, barType, bar):
    return get_md5("%s %d %s" % (symbol, barType, bar.get_date_time()))

def write_intermediate_csv(symbol, csvFiles, csvToUpload):
    csvToUpload.write("key,symbol,barType,date_time,open_,close_,high,low,volume,adj_close\n")

    symbol = symbol.upper()
    barType = 1

    feed = csvfeed.YahooFeed()
    for csvFile in csvFiles:
        print "Loading bars from %s" % csvFile
        feed.add_bars_from_csv(symbol, csvFile)

    print "Writing intermediate csv into %s" % csvToUpload.name
    for bars in feed:
        bar = bars.get_bar(symbol)
        csvToUpload.write("%s,%s,%d,%s,%s,%s,%s,%s,%s,%s\n" % (
            gen_bar_key(symbol, barType, bar),
            symbol,
            barType,
            datetimeToCSV(bar.get_date_time()),
            bar.get_open(),
            bar.get_close(),
            bar.get_high(),
            bar.get_low(),
            bar.get_volume(),
            bar.get_adj_close()
            ))
    csvToUpload.flush()

def upload_intermediate_csv(options, csvPath):
    print "Uploading %s" % csvPath
    cmd = []
    if options.appcfg_path:
        cmd.append(os.path.join(options.appcfg_path, "appcfg.py"))
    else:
        cmd.append("appcfg.py")
    cmd.append("upload_data")
    cmd.append("--kind=Bar")
    cmd.append("--filename=%s" % csvPath)
    cmd.append("--config_file=%s" % os.path.join(upload_barsPath, "bulkloader.yaml"))
    cmd.append("--url=%s" % options.url)

    popenObj = subprocess.Popen(args=cmd)
    popenObj.communicate()

def main():
    try:
        (options, args) = parse_cmdline()
        csvToUpload = tempfile.NamedTemporaryFile()
        write_intermediate_csv(options.symbol, args, csvToUpload)
        upload_intermediate_csv(options, csvToUpload.name)
    except Exception, e:
        sys.stdout.write("Error: %s\n" % e)
        sys.exit(1)

if __name__ == "__main__":
    main()
