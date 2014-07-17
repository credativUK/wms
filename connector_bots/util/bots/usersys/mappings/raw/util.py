# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bots open source edi translator
#    Copyright (C) 2014 credativ ltd (<http://www.credativ.co.uk>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from lxml import etree

def parse_dsv_xml(data, schema):
    def recursive_dict(element):
        return {element.tag: list(map(recursive_dict, element)) or element.text,}

    parser = etree.XMLParser(dtd_validation=True)
    schema_root = etree.parse(schema)
    schema = etree.XMLSchema(schema_root)
    parser = etree.XMLParser(schema = schema)
    data_root = etree.fromstring(data, parser)

    data_dicts = recursive_dict(data_root)
    return data_dicts

def simplify_dsv_xml(data, repeat_keys=["Segment_number",]):
    data_dicts = {}
    # Dictionaries - just continue
    if type(data) is dict:
        for key in data:
            data_dicts[key] = simplify_dsv_xml(data[key], repeat_keys)
    # Tuples - try and resolve the keys into a list of flat dictionaries
    elif type(data) in (list, tuple):
        newdict = {}
        newlist = []
        for l in data:
            assert len(l) == 1, "Unexpected data format"
            key = l.keys()[0]
            if key in repeat_keys and newdict:
                newlist.append(newdict)
                newdict = {}
            newdata = simplify_dsv_xml(l[key], repeat_keys)
            if type(newdata) in (dict,):
                newdict.setdefault(key, []).append(newdata)
            elif type(newdata) in (list, tuple,):
                newdict.setdefault(key, []).extend(newdata)
            else:
                newdict[key] = newdata
        if newdict:
            newlist.append(newdict)
        data_dicts = newlist
    else:
        data_dicts = data
    return data_dicts

def get_datetime(date, time):
    if not date:
        return None
    if not time:
        time = "0000"
    if len(date) == 6:
        date = "20"+date
    return "%s-%s-%s %s:%s:00" % (date[0:4], date[4:6], date[6:8], time[0:2], time[2:4])

def get_address(add_no, add_no_suf, add_1, add_2, add_3, add_4):
    add_no = add_no or ""
    add_no_suf = add_no_suf or ""
    add_1 = add_1 or ""
    add_2 = add_2 or ""
    add_3 = add_3 or ""
    add_4 = add_4 or ""

    ADD_LINE1 = (add_no + add_no_suf + " " + add_1).strip()
    if not ADD_LINE1:
        WH_ADD_LINE1 = add_2
    ADD_LINE2 = add_3
    ADD_LINE3 = add_4

    return ADD_LINE1, ADD_LINE2, ADD_LINE3
