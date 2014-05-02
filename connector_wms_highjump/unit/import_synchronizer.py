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
from openerp.addons.connector.unit.synchronizer import ImportSynchronizer
from ..backend import highjump
from ..connector import get_environment, add_checkpoint

_logger = logging.getLogger(__name__)

class HighJumpImportSynchronizer(ImportSynchronizer):
    """ Base importer for High Jump """

    def _before_import(self):
        """ Hook called before the import, when we have the High Jump data"""

    def _after_import(self, binding_id):
        """ Hook called at the end of the import """
        return

