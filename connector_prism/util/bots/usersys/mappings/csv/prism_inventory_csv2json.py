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

from datetime import datetime

def main(inn,out):

    pinn = inn.getloop({'BOTSID': 'LINE'})
    lout = out.putloop({'BOTSID':'inventory'})

    for line in pinn:
        SL_ID = line.get({'BOTSID': 'LINE', 'ID': None})
        SL_DATETIME = line.get({'BOTSID': 'LINE', 'datetime': None})
        if SL_DATETIME:
            SL_DATETIME = datetime.strptime(SL_DATETIME, '%d/%m/%Y %H:%M').strftime('%Y-%m-%d %H:%M:%S')
        else:
            SL_DATETIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        SL_PRODUCT = line.get({'BOTSID': 'LINE', 'sku': None})
        SL_QTY_TOTAL = line.get({'BOTSID': 'LINE', 'qty': None})

        oout = lout.putloop({'BOTSID': 'inventory'}, {'BOTSID':'inventory_line'})
        oout.put({'BOTSID':'inventory_line', 'datetime': SL_DATETIME})
        oout.put({'BOTSID':'inventory_line', 'product': SL_PRODUCT})
        oout.put({'BOTSID':'inventory_line', 'qty_total': SL_QTY_TOTAL})
        oout.put({'BOTSID':'inventory_line', 'qty_available': SL_QTY_TOTAL})
