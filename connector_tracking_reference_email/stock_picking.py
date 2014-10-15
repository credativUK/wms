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
from datetime import datetime
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector_ecommerce.event import on_picking_out_done, on_tracking_number_added
from openerp.addons.connector.connector import install_in_connector

from openerp.osv import orm, fields

_logger = logging.getLogger(__name__)

@on_picking_out_done
def picking_confirmed(session, model_name, picking_id, picking_method):
    _logger.debug('Creating job for picking ' + picking_id.__str__())
    picking = session.pool.get('stock.picking').read(session.cr, session.uid, picking_id, ['carrier_tracking_ref',])
    eta = 0
    if not picking['carrier_tracking_ref']:
        eta = 60*60*24
    server_action_id = session.pool.get('ir.model.data').get_object_reference(
            session.cr, session.uid,
            'connector_tracking_reference_email',
            'track_reference_action')[1]

    generate_email.delay(session, model_name, picking_id, server_action_id,eta=eta)

@on_tracking_number_added
def tracking_number_added(session, model_name, record_id):
    _logger.debug('Tracking number updated for picking ' + record_id.__str__())
    # Only way to check picking id linked with a job is in the function string - would be nicer with regex, but nevermind.
    matches = ['|','|',
        ('func_string','like',"openerp.addons.email_tracking_reference.stock_picking.generate_email(%%, %s,%%" % (record_id,)),
        ('func_string','like',"openerp.addons.email_tracking_reference.stock_picking.generate_email(%%, %sL%%" % (record_id,)),
        ('func_string','like',"openerp.addons.email_tracking_reference.stock_picking.generate_email(%%, %s)%%" % (record_id,)),
        ]
    job_ids = session.pool.get('queue.job').search(session.cr, session.uid, matches)
    if job_ids:
        session.pool.get('queue.job').write(session.cr, session.uid, job_ids, {'eta':datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

@job
def generate_email(session, model_name, picking_id, server_action_id):
    _logger.debug('Executing job for picking %s' % (picking_id,))
    if not hasattr(server_action_id, '__iter__'):
        server_action_id = [server_action_id]
    action_context = dict(session.context, active_id=picking_id)
    session.pool.get('ir.actions.server').run(session.cr, session.uid, server_action_id, action_context)

install_in_connector()
