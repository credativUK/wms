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

from openerp.addons.connector.event import Event

on_picking_out_done = Event()
"""
``on_picking_out_done`` is fired when an outgoing picking has been
marked as done.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""

on_picking_out_available = Event()
"""
``on_picking_out_available`` is fired when an outgoing picking has been
marked as available.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""

on_picking_in_available = Event()
"""
``on_picking_in_available`` is fired when an incoming picking has been
marked as available.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""

on_picking_out_cancel = Event()
"""
``on_picking_out_cancel`` is fired when an outgoing picking has been
cancelled.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""

on_picking_in_cancel = Event()
"""
``on_picking_in_cancel`` is fired when an incoming picking has been
cancelled.

Listeners should take the following arguments:

 * session: `connector.session.ConnectorSession` object
 * model_name: name of the model
 * record_id: id of the record
"""
