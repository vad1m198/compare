#!/usr/bin/env python
# Copyright (C) 2010 Samuel Abels.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Utilities for formating a diff_match_patch diff array into
a pretty two-column HTML table.
"""
from cgi              import escape
from diff_match_patch import diff_match_patch as dmp
 
def _line_iter(diffs):
    """
    A generator that lets you iterate over a diff array such that
    lines are always broken into separate chunks of data, and such
    that the current line number is returned, i.e.::
 
        for op, line_number, data in _line_iter(diffs):
            ...
    """
    lineno = 1
    for op, data in diffs:
        lines = data.split('\n')
        for i, line in enumerate(lines[:-1]):
            yield op, lineno + i, line + '\n'
        lineno += data.count('\n')
        yield op, lineno, lines[-1]
 
def _remove_equal_lines(diffs):
    """
    Given a diff array, this function returns a new array where equal
    lines are removed (except for equal lines directly before and after a
    change).
 
    It returns a new array containing 4-tuples (op, has_change, lineno,
    data), where::
 
        - op and data are equivalent to the corresponding elements in
        the source array
        - has_change is True if the current item is in a changed
        line, and False if it is an extra line (directly before or after
        a change).
        - lineno is the number of the current line.
    """
    # Identify changed lines.
    extra   = set()
    changed = set()
    for op, lineno, data in _line_iter(diffs):
        if op != dmp.DIFF_EQUAL:
            # Mark changed lines, as well as one line before and after it.
            extra.add(max(1, lineno - 1))
            changed.add(lineno)
            extra.add(lineno + 1)
 
    # Filter changed lines.
    result = []
    for op, lineno, data in _line_iter(diffs):
        if lineno in changed:
            result.append((op, True, lineno, data))
        elif lineno in extra:
            result.append((op, False, lineno, data))
    return result
 
def diff2html(diffs, left_label = None, right_label = None):
    """
    Given a diff array, this function returns a pretty two-column HTML
    table.
    """
    line_html   = []
    left_html   = []
    right_html  = []
    last_lineno = 0
    for op, has_change, lineno, data in _remove_equal_lines(diffs):
        # Append the line number to the first column of the table.
        if lineno > last_lineno + 1:
            line_html.append('<span><br/></span>')
            left_html.append('<br/>')
            right_html.append('<br/>')
        if lineno != last_lineno:
            line_html.append('<span>%d<br/></span>' % lineno)
        last_lineno = lineno
 
        # Append the left and right text to the second/third columns of
        # the table.
        text = escape(data.rstrip('\n'))
        if op == dmp.DIFF_INSERT:
            left_html.append('')
            right_html.append('<ins>%s</ins>' % text)
        elif op == dmp.DIFF_DELETE:
            left_html.append('<del>%s</del>' % text)
            right_html.append('')
        elif op == dmp.DIFF_EQUAL:
            left_html.append('<span>%s</span>' % text)
            right_html.append('<span>%s</span>' % text)
 
        if data.endswith('\n'):
            left_html.append('<br/>\n')
            right_html.append('<br/>\n')
 
    if not left_label and not right_label:
        head = ''
    else:
        head = '<tr>' \
             + '<th></th>' \
             + '<th>Version: %s</th>' % escape(left_label or '') \
             + '<th>Version: %s</th>' % escape(right_label or '') \
             + '</tr>'
    html = '<table class="diff"><tr>' \
         + head \
         + '<td class="line-numbers">' \
         + '\n'.join(line_html) \
         + '</td>' \
         + '<td class="expand">' \
         + ''.join(left_html) \
         + '</td>' \
         + '<td class="expand">' \
         + ''.join(right_html) \
         + '</td>' \
         + '</tr></table>'
    return html