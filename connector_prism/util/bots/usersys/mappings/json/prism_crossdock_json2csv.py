# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bots open source edi translator
#    Copyright (C) 2015 credativ ltd (<http://www.credativ.co.uk>). All Rights Reserved
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

def main(inn,out):

    pinn = inn.getloop({'BOTSID': 'crossdock'}, {'BOTSID': 'crossdock_line'})
    for line in pinn:

        PO_ID = line.get({'BOTSID': 'crossdock_line', 'po_id': None})
        LINE_INTERNAL_ID = line.get({'BOTSID': 'crossdock_line', 'move_id': None})
        LINE_QTY = line.get({'BOTSID': 'crossdock_line', 'product_qty': None})

        if not PO_ID:
            PO_ID = "999999" # Indicates no PO allocation in Prism (ie do not cross-dock)

        # JOIN LINES
        itr = 0
        for dummy in xrange(int(LINE_QTY or 0)):
            itr += 1
            LINE_QTY = 1.0
            LINE_UUID = "%s0%s" % (itr, LINE_INTERNAL_ID)

            main_out = out.putloop({'BOTSID': 'LINE'})
            main_out.put({'BOTSID':'LINE', 'itemID': LINE_UUID})
            main_out.put({'BOTSID':'LINE', 'poNumber': PO_ID})
