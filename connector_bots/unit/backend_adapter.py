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

import socket
import logging

from openerp import SUPERUSER_ID
from openerp import pooler
from openerp.addons.connector.unit.backend_adapter import CRUDAdapter
from openerp.addons.connector.exception import NetworkRetryableError, RetryableJobError

from datetime import datetime
import os
import time

_logger = logging.getLogger(__name__)

class BotsLocation(object):

    def __init__(self, location_in, location_archive, location_out):
        self.location_in = location_in
        self.location_archive = location_archive
        self.location_out = location_out

class BotsCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for Bots """

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(BotsCRUDAdapter, self).__init__(environment)
        self.bots = BotsLocation(self.backend_record.location_in,
                                       self.backend_record.location_archive,
                                       self.backend_record.location_out)

    def _get_unique_filename(self, pattern):
        file_obj = self.session.pool.get('bots.file')
        _cr = pooler.get_db(self.session.cr.dbname).cursor()
        try:
            loop_counter = 0
            while True:
                loop_counter += 1
                assert loop_counter < 50
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                file_name = pattern % (ts,)
                full_path = os.path.join(self.bots.location_out, file_name)

                files = file_obj.search(_cr, SUPERUSER_ID, [('full_path', '=', full_path)])
                if files:
                    _cr.commit()
                    time.sleep(0.1)
                    continue

                new_file = file_obj.create(_cr, SUPERUSER_ID, {'full_path': full_path, 'temp_path': full_path + ".tmp"})
                _cr.commit()
                _cr.execute("SELECT id FROM bots_file WHERE id = %s FOR UPDATE NOWAIT" % (new_file,))

                if os.path.isfile(full_path) or os.path.isfile(full_path + ".tmp"):
                    file_obj.unlink(_cr, SUPERUSER_ID, new_file)
                    _cr.commit()
                    time.sleep(0.1)
                    continue

                _cr.commit()
                return new_file
        finally:
            _cr.close()

    def _search(self, pattern):
        """ Search the in location for the pattern, return a list of file names that match """

        # TODO: Do not return matches which are marked as being read in the DB
        raise NotImplementedError('NIE')


    def _read(self, filename_id):
        """ Open file for reading and return the contents as a python dict """

        # TODO: Test file is not already being read (check DB in new cursor)
        # TODO: Mark file as being read (new DB entry in new cursor and commit)
        # TODO: If this worker dies this DB entry should be invalid
        raise NotImplementedError('NIE')

    def _read_done(self, filename_id):
        """ Move the file to archive and remove the read lock """

        # TODO: Test we have the lock on this file (check DB in new cursor)
        # TODO: Move the file to the archive location
        # TODO: Remove the read lock
        raise NotImplementedError('NIE')

    def _write(self, filename_id, contents):
        """ Create a new file at the location with the contents converted to JSON """

        file_obj = self.session.pool.get('bots.file')
        _cr = pooler.get_db(self.session.cr.dbname).cursor()
        try:
            _cr.execute("SELECT id FROM bots_file WHERE id = %s FOR UPDATE NOWAIT" % (filename_id,))
            file = file_obj.browse(_cr, SUPERUSER_ID, filename_id)

            out_fd = open(file.temp_path, "wb")
            out_fd.write(contents)
            out_fd.close()

            os.rename(file.temp_path, file.full_path)
            _cr.commit()
            return True
        finally:
            _cr.close()
