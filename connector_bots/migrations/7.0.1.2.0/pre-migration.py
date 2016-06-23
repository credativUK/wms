# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Ondřej Kuzník
#    Copyright 2016 credativ, ltd.
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

logger = logging.getLogger('upgrade')


def migrate(cr, version):
    """
    The cancellation export setting is now a selection.
    """
    if version:  # do not run on a fresh DB, see lp:1259975
        logger.info("Migrating connector_bots from version %s", version)
        cr.execute("ALTER TABLE bots_backend ALTER "
                   "      COLUMN feat_picking_out_cancel"
                   "      TYPE character varying "
                   "      USING CASE WHEN feat_picking_out_cancel THEN 'export' "
                   "            ELSE 'reject' END")
        cr.execute("ALTER TABLE bots_backend ALTER "
                   "      COLUMN feat_picking_in_cancel"
                   "      TYPE character varying "
                   "      USING CASE WHEN feat_picking_in_cancel THEN 'export' "
                   "            ELSE 'reject' END")
