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

{'name': 'Connector for Bots EDI server - Prism',
 'version': '1.0.0',
 'category': 'Connector',
 'author': 'credativ Ltd',
 'website': 'http://www.credativ.co.uk',
 'license': 'AGPL-3',
 'description': """
Connector for Bots EDI server - Prism
=====================================

This module provides Prism specific changes to the connector Bots interface
""",
 'depends': [
     'connector_bots',
 ],
 'data': [
     'bots_model_view.xml',
     'bots_data.xml',
     'stock_view.xml',
     'purchase_view.xml',
     'bots_menu.xml',
 ],
 'installable': True,
}
