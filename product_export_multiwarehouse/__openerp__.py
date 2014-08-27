# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Ondrej Kuznik
#    Copyright 2014 credativ ltd.
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

{'name': 'Magento coalesce warehouse stock',
 'version': '1.0.0',
 'category': 'Connector',
 'depends': ['magentoerpconnect',
             ],
 'author': 'credativ ltd.',
 'license': 'AGPL-3',
 'description': """
Magento coalesce warehouse stock
================================

Makes it possible to export the cumulative stock image of multiple warehouses
to a single shop.

Might make order import request more stock than available in the default
warehouse, this has to be reallocated manually.
""",
 'data': [
     "magento_store.xml",
     ],
 'installable': True,
 'application': False,
}

