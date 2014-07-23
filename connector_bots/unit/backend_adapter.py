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
from suds.client import Client

from openerp.addons.connector.unit.backend_adapter import CRUDAdapter
from openerp.addons.connector.exception import NetworkRetryableError, RetryableJobError

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

    def _search(self, pattern):
        """ Search the in location for the pattern, return a list of file names that match """

        # TODO: Do not return matches which are marked as being read in the DB
        raise NotImplementedError('NIE')


    def _read(self, filename):
        """ Open file for reading and return the contents as a python dict """

        # TODO: Test file is not already being read (check DB in new cursor)
        # TODO: Mark file as being read (new DB entry in new cursor and commit)
        # TODO: If this worker dies this DB entry should be invalid
        raise NotImplementedError('NIE')

    def _read_done(self, filename):
        """ Move the file to archive and remove the read lock """

        # TODO: Test we have the lock on this file (check DB in new cursor)
        # TODO: Move the file to the archive location
        # TODO: Remove the read lock
        raise NotImplementedError('NIE')

    def _write(self, filename, contents):
        """ Create a new file at the location with the contents converted to JSON """

        # TODO: Make sure the file is not currently being written to (check DB in new cursor)
        # TODO: Mark file as being written to (new DB entry in new cursor and commit)
        # TODO: If this worker dies this DB entry should be invalid
        # TODO: Create a new file with a temporary name, write contents, rename to destination filename
        # TODO: Clean up DB entry
        raise NotImplementedError('NIE')
