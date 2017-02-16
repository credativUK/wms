# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 credativ Ltd
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{'name': 'Shop connector for Bots EDI server',
 'version': '7.20161201.0',
 'category': 'Connector',
 'author': 'credativ Ltd',
 'website': 'http://www.credativ.co.uk',
 'license': 'AGPL-3',
 'description': """
Shop connector for Bots EDI server
==================================

This module provides a way for OpenERP to communicate shop data
with EDI systems through Bots which is used to translate to the
specific data format for the external EDI system.

This module has mappings to export data to Bots in JSON and then
forward this on to the external system using a specific version
of the X12 4010 EDI format.
""",
 'depends': [
     'connector_ecommerce',
     'connector_bots',
     'product_m2mcategories',
     'sale_payment_method',
 ],
 'data': [
     'bots_model_view.xml',
     'data.xml',
     'product_view.xml',
     'security/ir.model.access.csv',
 ],
 'installable': True,
 }
