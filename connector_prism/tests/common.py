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

"""
Helpers usable in the tests
"""

import openerp.tests.common as common
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import _unpickle, Job

from ..unit.backend_adapter import BotsCRUDAdapter, file_to_process
from ..connector import get_environment

import tempfile
import shutil
from functools import partial

class SetUpBotsBase(common.TransactionCase):
    """ Base class - Test the sync from a Bots simulated instance.

    Set up bots warehouses
    """

    def _run_job(self, job_id):
        job_obj = self.registry('queue.job')
        job = job_obj.browse(self.cr, self.uid, job_id)
        (func_name, args, kwargs) = _unpickle(job.func)
        runnable_job = Job(func=func_name, args=args, kwargs=kwargs, priority=job.priority, eta=None, job_uuid=job.uuid, description=job.name)
        runnable_job.user_id = self.session.uid
        return runnable_job.perform(self.session)

    def _get_file_data(self, model, pattern):
        res = {}
        env = get_environment(self.session, model, self.backend_id)
        adapter = BotsCRUDAdapter(env)
        file_ids = adapter._search(pattern, location='out')
        for file_id in file_ids:
            with file_to_process(self.session, file_id[0], new_cr=False) as f:
                res[file_id] = f.read()
        return res

    def _set_file_data(self, model, pattern, data):
        res = {}
        env = get_environment(self.session, model, self.backend_id)
        adapter = BotsCRUDAdapter(env)
        file_id = adapter._get_unique_filename(pattern, location='in')
        adapter._write(file_id, data)
        return True

    def setUp(self):
        super(SetUpBotsBase, self).setUp()
        self.backend_model = self.registry('bots.backend')
        self.session = ConnectorSession(self.cr, self.uid)
        data_model = self.registry('ir.model.data')
        self.get_ref = partial(data_model.get_object_reference, self.cr, self.uid)
        backend_ids = self.backend_model.search( self.cr, self.uid, [('name', '=', 'Test Bots')])
        if backend_ids:
            self.backend_id = backend_ids[0]
        else:
            __, warehouse_id = self.get_ref('stock', 'warehouse0')

            self.location_in = tempfile.mkdtemp(prefix = 'bots_test_in_')
            self.location_archive = tempfile.mkdtemp(prefix = 'bots_test_archive_')
            self.location_out = tempfile.mkdtemp(prefix = 'bots_test_out_')

            self.backend_id = self.backend_model.create(
                self.cr,
                self.uid,
                {
                    'name': 'Test Bots',
                    'version': '3.1.0',
                    'name_from': 'Bots Test',
                    'name_to': 'OpenERP Test',
                    'location_in': self.location_in,
                    'location_archive': self.location_archive,
                    'location_out': self.location_out,
                    'feat_picking_out': True,
                    'feat_picking_in': True,
                    'feat_picking_out_cancel': 'export',
                    'feat_picking_in_cancel': 'export',
                    'feat_picking_out_conf': True,
                    'feat_picking_in_conf': True,
                    'feat_inventory_in': True,
                })

            self.bots_warehouse_id = self.registry('bots.warehouse').create(
                self.cr,
                self.uid,
                {
                    'backend_id': self.backend_id,
                    'warehouse_id': warehouse_id,
                    'name': 'Test Bots Warehouse',
                    'bots_id': 'Test Bots Warehouse',
                })

    def tearDown(self):
        shutil.rmtree(self.location_in)
        shutil.rmtree(self.location_archive)
        shutil.rmtree(self.location_out)
        super(SetUpBotsBase, self).tearDown()
