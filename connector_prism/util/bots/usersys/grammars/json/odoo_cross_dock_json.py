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

from bots.botsconfig import *

syntax = { 
        'indented': True,
    }

structure = [
{ID:'crossdock',MIN:1,MAX:999999,
    QUERIES:{
        'frompartner':  ({'BOTSID':'messages'},{'BOTSID':'header','partner_name':None}),
        'topartner':    ({'BOTSID':'messages'},{'BOTSID':'header','partner_name':None}),
        'reference':    ({'BOTSID':'messages'},{'BOTSID':'header','msg_id':None}),
        'testindicator':({'BOTSID':'messages'},{'BOTSID':'header','test':None})},
    LEVEL:[
        {ID:'header',MIN:0,MAX:1},
        {ID:'crossdock_line',MIN:0,MAX:999999},
        ]},
]

recorddefs = {
    'crossdock':[
            ['BOTSID', 'M', 64, 'AN'],
          ],
    'header':[
            ['BOTSID', 'M', 64, 'AN'],
            ['partner_to', 'C', 20, 'AN'],
            ['partner_from', 'C', 64, 'AN'],
            ['message_id', 'C', 64, 'AN'],
            ['test', 'C', 64, 'AN'],
            ['date_msg', 'C', 64, 'AN'],
          ],
    'crossdock_line':[
            ['BOTSID', 'M', 64, 'AN'],
            ['move_id','M', 64,'N'],
            ['product_qty','M', 64,'N'],
            ['po_id', 'M', 64, 'AN'],
          ],
     }

