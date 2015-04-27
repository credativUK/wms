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

from openerp.osv import orm, fields, osv
from openerp import pooler, netsvc, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.exception import JobError, NoExternalId
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer

from .unit.binder import BotsModelBinder
from .unit.backend_adapter import BotsCRUDAdapter, file_to_process
from .backend import bots
from .connector import get_environment, add_checkpoint

import json
import traceback
from datetime import datetime

class StockWarehouse(orm.Model):
    _inherit = 'stock.warehouse'

    def purchase_cutoff(self, cr, uid, ids, context=None):
        return NotImplementedError() # TODO

@job
def purchase_cutoff(session, model_name, record_id, new_cr=True):
    warehouse = session.browse(model_name, record_id)
    return warehouse.purchase_cutoff()
