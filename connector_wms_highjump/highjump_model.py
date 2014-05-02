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

import logging
from openerp.osv import fields, orm
import openerp.addons.connector as connector
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.unit.mapper import mapping, only_create, ImportMapper
from .backend import highjump
from .connector import add_checkpoint

_logger = logging.getLogger(__name__)


class highjump_backend(orm.Model):
    _name = 'highjump.backend'
    _description = 'High Jump Backend'
    _inherit = 'connector.backend'

    _backend_type = 'highjump'

    def _select_versions(self, cr, uid, context=None):
        return [('seko', 'Seko')]

    _columns = {
        'version': fields.selection(
            _select_versions,
            string='Version',
            required=True),
        'location': fields.char('Location', required=True),
        'username': fields.char('Username'),
        'warehouse_ids': fields.one2many('highjump.warehouse', 'backend_id', string='Warehouse Mapping', readonly=True),
        'default_lang_id': fields.many2one(
            'res.lang',
            'Default Language',
            help="If a default language is selected, the records "
                 "will be imported in the translation of this language.\n"
                 "Note that a similar configuration exists for each storeview."),
    }

class highjump_warehouse(orm.Model):
    _name = 'highjump.warehouse'
    _inherit = 'highjump.binding'
    _description = 'High Jump Warehouse Mapping'

    _columns = {
        'name': fields.char('Name', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
    }

    _sql_constraints = [
        ('highjump_warehouse_uniq', 'unique(backend_id, highjump_id)',
         'A warehouse mapping with the same ID on High Jump already exists.'),
    ]
