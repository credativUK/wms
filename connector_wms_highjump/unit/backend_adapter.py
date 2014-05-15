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

class HighJumpLocation(object):

    def __init__(self, location, username, hj_order_prefix, hj_priority, hj_service_level):
        self.location = location
        self.username = username
        self.hj_order_prefix = hj_order_prefix
        self.hj_priority = hj_priority
        self.hj_service_level = hj_service_level

class HighJumpCRUDAdapter(CRUDAdapter):
    """ External Records Adapter for HighJump """

    def __init__(self, environment):
        """

        :param environment: current environment (backend, session, ...)
        :type environment: :py:class:`connector.connector.Environment`
        """
        super(HighJumpCRUDAdapter, self).__init__(environment)
        self.highjump = HighJumpLocation(self.backend_record.location,
                                       self.backend_record.username,
                                       self.backend_record.hj_order_prefix,
                                       self.backend_record.hj_priority,
                                       self.backend_record.hj_service_level)

    def _call(self, method, arguments):
        try:
            api = Client(location=self.highjump.location+'/pubfun/warehouse.asmx',
                         url=self.highjump.location+'/pubfun/warehouse.asmx?WSDL')
            result = getattr(api.service, method)(**arguments)
            _logger.debug("api.call(%s, %s) returned %s",
                        method, arguments, result)
            return result
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                'A network error caused the failure of the job: '
                '%s' % err)
