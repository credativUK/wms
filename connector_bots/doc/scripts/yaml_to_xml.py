#!/usr/bin/env python

#SCHEMA = "../schemas/StockReport_schema_credativ_20140625.xsd"
#DATA = "../examples/StockReport_20140623145617941_NRI_corrected.yaml"
#DATA = "../examples/StockReport_v1301_DSV.yaml"

SCHEMA = "../schemas/WarehouseEntryOrder_schema_credativ_20140625.xsd"
DATA = "../examples/WarehouseEntryOrder_example_credativ_20140708.yaml"

#SCHEMA = "../schemas/WarehouseOrderConfirmation_schema_credativ_20140625.xsd"
#DATA = "../examples/WarehouseOrderConfirmation_v1401_DSV.yaml"

#SCHEMA = "../schemas/WarehouseShippingOrder_schema_credativ_20140625.xsd"
#DATA = "../examples/WarehouseShippingOrder_example_credativ_20140707.yaml"

from lxml import etree
import yaml

DOCTYPE = '<?xml version="1.0" encoding="UTF-8"?>'

def serialize(d):
    assert len(d.keys()) == 1, 'Cannot encode more than one root element'
    name = d.keys()[0]
    root = etree.Element(name)
    populate_element(root, d[name])
    return '%s\n%s' % (DOCTYPE, etree.tostring(root, pretty_print=True))

def populate_element(element, d):
    if type(d) in (tuple, list):
        for e in d:
            populate_element(element, e)
    elif type(d) is dict:
        for k, v in d.iteritems():
            if type(v) is dict:
                child = etree.Element(k)
                populate_element(child, v)
                element.append(child)
            elif type(v) is list:
                if k[-1] == 's':
                    name = k[:-1]
                else:
                    name = k
                child = etree.Element(name)
                for item in v:
                    populate_element(child, item)
                element.append(child)
            else:
                child = etree.Element(k)
                child.text = unicode(v or '')
                element.append(child)
    else:
        raise ValueError("Don't know how to serialize type %s" % (type(d)))

yaml_file = file(DATA, 'r')
data_yaml = yaml.load_all(yaml_file)
data_dict = [x for x in data_yaml]
assert len(data_dict) == 1, 'Cannot encode more than one root element'
data_xml = serialize(data_dict[0])

# Sanity check to make sure our output passes validation
parser = etree.XMLParser(dtd_validation=True)
schema_root = etree.parse(SCHEMA)
schema = etree.XMLSchema(schema_root)
parser = etree.XMLParser(schema = schema)
data_root = etree.fromstring(data_xml, parser)

#import ipdb; ipdb.set_trace()
print data_xml


