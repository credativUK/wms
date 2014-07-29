# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 credativ Ltd (<http://credativ.co.uk>).
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
from datetime import datetime
from openerp.addons.connector.queue.job import job 
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.event import Event
from openerp.addons.connector_ecommerce.event import on_picking_out_done, on_tracking_number_added
from openerp.addons.connector.connector import install_in_connector

from openerp.osv import orm, fields

_logger = logging.getLogger(__name__)

on_picking_confirmed = Event()

class stock_picking(orm.Model):
    _inherit = 'stock.picking'

    def action_confirm(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).action_confirm(cr, uid,
                                                     ids, context=context)
                                                     
        pickings = self.browse(cr, uid, ids, context=context)
        
        session = ConnectorSession(cr, uid, context=context)
        server_action_id = self._get_ids(session.cr, session.uid, 'ir.actions.server', 'track_reference_action')
        
        for picking in pickings:
            if picking.type == 'out':
                on_picking_confirmed.fire(session, self._name, picking.id, server_action_id)

        
      
        return res
        
    def _get_ids(self, cr, uid, model, name):
        data_pool = self.pool.get('ir.model.data')
        ids = data_pool.search(cr, uid, [('model', '=', model), ('name', '=', name)])
        return [data.res_id for data in data_pool.browse(cr, uid, ids)]


@on_picking_confirmed
def picking_confirmed(session, model_name, picking_id, server_action_id):
    _logger.debug('Creating job for picking ' + picking_id.__str__())
    picking = session.pool.get('stock.picking').read(session.cr, session.uid, picking_id)
    eta = 0
    if not picking['carrier_tracking_ref']:
        eta = 60*60*24
    generate_email.delay(session, model_name, picking_id, server_action_id,eta=eta)


@on_tracking_number_added
def tracking_number_added(session, model_name, record_id):
    _logger.debug('Tracking number updated for picking ' + record_id.__str__())
    #Only way to check picking id linked with a job is in the function string
    job_ids = session.pool.get('queue.job').search(session.cr, session.uid, [('func_string','like',"openerp.addons.email_tracking_reference.stock_picking.generate_email(%, " + record_id.__str__() + "%")])
    
    for job_id in job_ids:
        session.pool.get('queue.job').write(session.cr, session.uid, job_id,{'eta':datetime.now().strftime("%Y-%m-%d %H:%M:%S")})



@job
def generate_email(session, model_name, picking_id, server_action_id):
    _logger.debug('Executing job for picking '+ picking_id.__str__())
    action_context = dict(session.context, active_id=picking_id)
    session.pool.get('ir.actions.server').run(session.cr, session.uid, server_action_id, action_context)
    
    

install_in_connector()
