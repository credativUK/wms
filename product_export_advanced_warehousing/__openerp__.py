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

{'name': 'Magento stock export for Advanced Warehousing module',
 'version': '1.0.0',
 'category': 'Connector',
 'depends': ['magentoerpconnect',
             ],
 'author': 'credativ ltd.',
 'license': 'AGPL-3',
 'description': """
Magento stock export for Advanced Warehousing module
================================

Makes it possible to export the stock levels towards a magento using the Advanced Warehousing module.

Will only export the locations configured for the backend.
""",
 'data': [
     "magento_store.xml",
     ],
 'installable': True,
 'application': False,
}
