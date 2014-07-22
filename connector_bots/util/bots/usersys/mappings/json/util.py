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
from datetime import datetime
from collections import OrderedDict

DOCTYPE = '<?xml version="1.0" encoding="UTF-8"?>'

def serialize_dsv_xml(d, SCHEMA):
    def populate_element(element, d):
        if type(d) in (tuple, list):
            for e in d:
                populate_element(element, e)
        elif type(d) in (dict, OrderedDict):
            for k, v in d.iteritems():
                if type(v) in (dict, OrderedDict):
                    child = etree.Element(k)
                    populate_element(child, v)
                    element.append(child)
                elif type(v) is list: # The entire element will repeat, eg <order><name>123</name></order> <order><name>456</name></order>
                    for item in v:
                        child = etree.Element(k)
                        populate_element(child, item)
                        element.append(child)
                elif type(v) is tuple: # Only the sequence in the XML element will repeat eg <order><name>123</name> <name>456</name></order>
                    child = etree.Element(k)
                    for item in v:
                        populate_element(child, item)
                    element.append(child)
                else:
                    child = etree.Element(k)
                    child.text = unicode(v or '')
                    element.append(child)
        else:
            raise ValueError("Don't know how to serialize type %s" % (type(d)))

    def validate_xml(data):
        parser = etree.XMLParser(dtd_validation=True)
        schema_root = etree.parse(SCHEMA)
        schema = etree.XMLSchema(schema_root)
        parser = etree.XMLParser(schema = schema)
        data_root = etree.fromstring(data, parser)
        return True

    assert len(d.keys()) == 1, 'Cannot encode more than one root element'
    name = d.keys()[0]
    root = etree.Element(name)
    populate_element(root, d[name])
    xml_data = '%s\n%s' % (DOCTYPE, etree.tostring(root, pretty_print=True))
    validate_xml(xml_data)
    return xml_data

def get_datetime(dt, format="%Y-%m-%d %H:%M:%S.%f", c=True, s=False):
    if not dt:
        return None, None
    date_dt = datetime.strptime(dt, format)
    date = date_dt.strftime(c and "%Y%m%d" or "%y%m%d")
    time = date_dt.strftime(s and "%H%M%S" or "%H%M")
    return date, time

lang_map = [
    # [ISO3 code, ISO2 code, DSV language code, English name],
    ['swe', 'sv', 'A', 'Swedish'],
    ['fin', 'fi', 'B', 'Finnish'],
    ['dan', 'da', 'C', 'Danish'],
    ['dut', 'nl', 'D', 'Dutch'],
    ['nld', 'nl', 'D', 'Dutch'],
    ['eng', 'en', 'E', 'English'],
    ['fre', 'fr', 'F', 'French'],
    ['fra', 'fr', 'F', 'French'],
    ['ger', 'de', 'G', 'German'],
    ['deu', 'de', 'G', 'German'],
    ['ita', 'it', 'I', 'Italian'],
    ['nob', 'nb', 'N', 'Norwegian'],
    ['por', 'pt', 'P', 'Portuguese'],
    ['spa', 'es', 'S', 'Spanish'],
    ['hun', 'hu', 'H', 'Hungarian'],
    ['gle', 'ga', 'J', 'Irish'],
    ['lav', 'lv', 'K', 'Lettish'],
    ['pol', 'pl', 'L', 'Polish'],
    ['mlt', 'mt', 'M', 'Maltese'],
    ['lit', 'lt', 'O', 'Lithuanian'],
    ['rum', 'ro', 'Q', 'Romanian'],
    ['rom', 'ro', 'Q', 'Romanian'],
    ['rus', 'ru', 'R', 'Russian'],
    ['cze', 'cs', 'T', 'Czech'],
    ['ces', 'cs', 'T', 'Czech'],
    ['slo', 'sk', 'U', 'Slovak'],
    ['slk', 'sk', 'U', 'Slovak'],
    ['gre', 'el', 'V', 'Greek'],
    ['ell', 'el', 'V', 'Greek'],
    ['est', 'et', 'W', 'Estonian'],
    ['bul', 'bg', 'X', 'Bulgarian'],
    ['slv', 'sl', 'Z', 'Slovenian'],
]

def get_dsv_lang(lang):
    lang = (lang or 'en_GB').lower()

    # Test ISO3 codes
    for lm in lang_map:
        if lm[0] == lang[:3]:
            return lm[2]
    # Test ISO2 codes
    for lm in lang_map:
        if lm[1] == lang[:2]:
            return lm[2]

    return 'E' # If none found, use English
