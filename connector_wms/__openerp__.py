# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2014 credativ Ltd
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

{'name': 'Connector for WMS',
 'version': '1.0.0',
 'category': 'Connector',
 'author': 'credativ Ltd',
 'website': 'http://www.credativ.co.uk',
 'license': 'AGPL-3',
 'description': """
Connector for WMS
=================

This modules aims to be a common layer for the connectors dealing with
Warehouse Management.

It sits on top of the `connector`_ framework and is used by the
WMS connectors.

That's a technical module, which include amongst other things:

Events

    On which the connectors can subscribe consumers
    (Picking assigned, ...)

""",
 'depends': [
     'connector',
     'connector_ecommerce',
     'delivery',
 ],
 'data': [
     'wms_data.xml'
 ],
 'installable': True,
}
