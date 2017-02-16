# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2016 credativ Ltd
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

{
    'name': 'BOTS Connector Magento Bundle Support',
    'version': '1.0',
    'category': 'Connector',
    'author': 'credativ Ltd',
    'website': 'http://www.credativ.co.uk',
    'license': 'AGPL-3',
    'description': '''
This module adds an awareness of Magento bundles to the BOTS connector, and ensures that these are kept together when splitting pickings.
    ''',
    'depends': [
        'connector_bots',
        'magento_bundle_availability', # https://github.com/credativUK/credativ-addons
    ],
    'data': [
    ],
    'installable': True,
    'active' : False,
}
