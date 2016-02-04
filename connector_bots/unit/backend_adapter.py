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
from contextlib import contextmanager
import os
import time
import re

_logger = logging.getLogger(__name__)

@contextmanager
def file_to_process(session, filename_id, new_cr=True):
    """
        Open file for reading and return the contents as a stream.

        If new_cr is true, everything is handled in a separate transaction that
        is committed on successful completion and file then moved away to the
        archive location.

        If new_cr is False, caller accepts the potential data loss arising from
        the fact that the uncommitted state may still be rolled back after the
        file and state has already been archived.
    """
    fd = None

    file_obj = session.pool.get('bots.file')
    try:
        cr = pooler.get_db(session.cr.dbname).cursor()
        if new_cr:
            orig_cr = session.cr
            session.cr = cr

        cr.execute("SELECT id FROM bots_file WHERE id = %s FOR UPDATE NOWAIT" % (filename_id,))
        ids = [x[0] for x in cr.fetchall()]
        if not ids: # We acquired 0 locks which means the bots_file record has already been processed
            raise RetryableJobError('The bots.file record %s is no longer available, the file may have already been processed by another thread, skipping.' % (filename_id,))
        file = file_obj.browse(cr, SUPERUSER_ID, filename_id)
        fd = open(file.full_path, "rb")
        yield fd
        file_obj.write(cr, SUPERUSER_ID, filename_id, {'processed': True})
        cr.commit()

        # If we committed, the file is marked as successfully processed and
        # noone else will try to do so again. It can be archived now but should
        # that fail, nothing happens, really, as anyone can do the move later
        os.rename(file.full_path, file.arch_path)
        file_obj.unlink(cr, SUPERUSER_ID, filename_id)
    except:
        cr.rollback()
        raise
    finally:
        if fd:
            fd.close()

        # we have already rolled back if there was an error
        if new_cr:
            session.cr = orig_cr

        cr.commit()
        cr.close()

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
                    file_id = file_id[0]

                    # Is this a leftover file that someone processed and could not move? Try again and log failure
                    f = file_obj.read(_cr, SUPERUSER_ID, file_id, ['processed', 'arch_path'], context=self.session.context)
                    if f['processed']:
                        try:
                            os.rename(file[1], f['arch_path'])
                            file_obj.unlink(_cr, SUPERUSER_ID, file_id)
                        except IOError, e:
                            _logger.exception('Error trying to move file %s -> %s', file[1], f['arch_path'])
                        continue
                else:
                    file_id = file_obj.create(_cr, SUPERUSER_ID, {'full_path': file[1], 'arch_path': file[2], 'temp_path': file[1] + ".tmp"}, context=self.session.context)
                file_ids.append((file_id, file[1]))
            _cr.commit()
        finally:
            _cr.close()
        return file_ids

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
