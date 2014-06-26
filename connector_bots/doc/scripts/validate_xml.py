#!/usr/bin/env python

SCHEMA = "../schemas/WarehouseOrderConfirmation_schema_credativ_20140625.xsd"
DATA = "../examples/WarehouseOrderConfirmation_v1401_DSV.xml"

from lxml import etree

parser = etree.XMLParser(dtd_validation=True)
schema_root = etree.parse(SCHEMA)
schema = etree.XMLSchema(schema_root)
parser = etree.XMLParser(schema = schema)

data_root = etree.parse(DATA, parser)
