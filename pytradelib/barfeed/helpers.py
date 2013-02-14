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

# Calculates session close based on days.
# When the current bar is the last bar for the day, or the last bar in the feed, the session is closed.
def session_close(current_bar, next_bar):
    ret = False
    if next_bar == None:
        ret = True
    elif current_bar.get_date_time().date() != next_bar.get_date_time().date():
        ret = True
    return ret

# Sets session close and bars till session close properties to bars in a sequence. 
def set_session_close_attributes(bar_seq, session_close_strategy=None):
    for i in xrange(1, len(bar_seq)):
        if session_close(bar_seq[i-1], bar_seq[i]):
            bar_seq[i-1].set_session_close(True)
            # Flag the penultimate bar if:
            # - There is a penultimate bar
            # - The penultimate and last bar belong to the same session.
            if i-2 >= 0 and session_close(bar_seq[i-2], bar_seq[i-1]) == False:
                bar_seq[i-2].set_bars_until_session_close(1)

    # Deal with the last bars in the feed.
    if len(bar_seq):
        bar_seq[-1].set_session_close(True)
        if len(bar_seq) > 1:
            bar_seq[-2].set_bars_until_session_close(1)
