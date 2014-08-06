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
import re

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

    def _get_unique_filename(self, pattern, location='out'):
        if location == 'out':
            loc = self.bots.location_out
        elif location == 'archive':
            loc = self.bots.location_archive
        else:
            loc = self.bots.location_in

        file_obj = self.session.pool.get('bots.file')
        _cr = pooler.get_db(self.session.cr.dbname).cursor()
        try:
            loop_counter = 0
            while True:
                loop_counter += 1
                assert loop_counter < 50
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                file_name = pattern % (ts,)
                full_path = os.path.join(loc, file_name)
                arch_path = os.path.join(self.bots.location_archive, file_name)

                files = file_obj.search(_cr, SUPERUSER_ID, [('full_path', '=', full_path)])
                if files:
                    _cr.commit()
                    time.sleep(0.1)
                    continue

                new_file = file_obj.create(_cr, SUPERUSER_ID, {'full_path': full_path, 'temp_path': full_path + ".tmp", 'arch_path': arch_path})
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

    def _search(self, pattern, location='in'):
        """
            Search the 'in' location for the pattern, return a list of file names that match
            he new files will not appear in the session cursor, a new cursor must be created
        """

        if location == 'out':
            loc = self.bots.location_out
        elif location == 'archive':
            loc = self.bots.location_archive
        else:
            loc = self.bots.location_in

        file_obj = self.session.pool.get('bots.file')
        _cr = pooler.get_db(self.session.cr.dbname).cursor()
        try:
            all = [(f, os.path.join(loc, f), os.path.join(self.bots.location_archive, f)) for f in os.listdir(loc)]
            matching_files = [x for x in all if re.match(pattern, x[0])]
            file_ids = []
            for file in matching_files:
                file_id = file_obj.search(_cr, SUPERUSER_ID, [('full_path', '=', file[1])], context=self.session.context)
                if file_id:
                    file_ids.extend(file_id)
                else:
                    file_id = file_obj.create(_cr, SUPERUSER_ID, {'full_path': file[1], 'arch_path': file[2], 'temp_path': file[1] + ".tmp"}, context=self.session.context)
                    file_ids.append(file_id)
            _cr.commit()
        finally:
            _cr.close()
        return file_ids

    class _read_mutex(object):
        _cr = None

        def __init__(self, dbname):
            self._cr = pooler.get_db(dbname).cursor()

        def __del__(self):
            self.free_cursor()

        def free_cursor(self):
            if self._cr:
                self._cr.close()
                self._cr = None

    def _read(self, filename_id):
        """
            Open file for reading and return the contents as a stream
            Returns the raw data and a mutex class containing a cursor with a lock on the file
        """
        file_obj = self.session.pool.get('bots.file')
        try:
            mutex = self._read_mutex(self.session.cr.dbname)
            mutex._cr.execute("SELECT id FROM bots_file WHERE id = %s FOR UPDATE NOWAIT" % (filename_id,))
            file = file_obj.browse(mutex._cr, SUPERUSER_ID, filename_id)
            in_fd = open(file.full_path, "rb")
            data = in_fd.read()
            in_fd.close()
            return data, mutex
        except Exception, e:
            del mutex
            raise e

    def _read_done(self, filename_id, mutex):
        """ Move the file to archive and remove the read lock """

        file_obj = self.session.pool.get('bots.file')
        try:
            file = file_obj.browse(mutex._cr, SUPERUSER_ID, filename_id)
            os.rename(file.full_path, file.arch_path)
            file_obj.unlink(mutex._cr, SUPERUSER_ID, filename_id)
        except Exception, e:
            del mutex
            raise e
        mutex._cr.commit()
        mutex.free_cursor()
        return True

    def _write(self, filename_id, contents):
        """ Create a new file at the location. Input must be a stream."""

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
