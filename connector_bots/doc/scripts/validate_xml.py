#!/usr/bin/env python

#SCHEMA = "../schemas/StockReport_schema_credativ.xsd"
#DATA = "../examples/StockReport_20140623145617941_NRI_corrected.xml"
#DATA = "../examples/StockReport_v1301_DSV.xml"

SCHEMA = "../schemas/WarehouseEntryOrder_schema_credativ.xsd"
DATA = "../examples/WarehouseEntryOrder_v1401_DSV.xml"

#SCHEMA = "../schemas/WarehouseOrderConfirmation_schema_credativ.xsd"
#DATA = "../examples/WarehouseOrderConfirmation_v1401_DSV.xml"

#SCHEMA = "../schemas/WarehouseShippingOrder_schema_credativ.xsd"
#DATA = "../examples/WarehouseShippingOrder_v1401_DSV.xml"

from lxml import etree
import yaml

def recursive_dict(element):
    return {element.tag: list(map(recursive_dict, element)) or element.text,}

parser = etree.XMLParser(dtd_validation=True)
schema_root = etree.parse(SCHEMA)
schema = etree.XMLSchema(schema_root)
parser = etree.XMLParser(schema = schema)

data_root = etree.parse(DATA, parser)

data_dicts = recursive_dict(data_root.getroot())
data_yaml = yaml.dump(data_dicts, default_flow_style=False)

#import ipdb; ipdb.set_trace()
print data_yaml
