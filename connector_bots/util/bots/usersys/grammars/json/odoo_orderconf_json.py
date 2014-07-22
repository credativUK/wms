# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bots open source edi translator
#    Copyright (C) 2014 credativ ltd (<http://www.credativ.co.uk>). All Rights Reserved
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
{ID:'orderconf',MIN:1,MAX:999999,
    QUERIES:{
        'frompartner':  ({'BOTSID':'messages'},{'BOTSID':'header','partner_name':None}),
        'topartner':    ({'BOTSID':'messages'},{'BOTSID':'header','partner_name':None}),
        'reference':    ({'BOTSID':'messages'},{'BOTSID':'header','msg_id':None}),
        'testindicator':({'BOTSID':'messages'},{'BOTSID':'header','test':None})},
    LEVEL:[
        {ID:'header',MIN:0,MAX:1},
        {ID:'shipment',MIN:0,MAX:999999,LEVEL:[
                {ID:'invoice',MIN:0,MAX:1},
                {ID:'references',MIN:0,MAX:9},
                {ID:'values',MIN:0,MAX:7},
                {ID:'partner',MIN:0,MAX:10},
                {ID:'line',MIN:0,MAX:999999,LEVEL:[
                        {ID:'references',MIN:0,MAX:9},
                    ]},
            ]},
        ]},
]

recorddefs = {
    'orderconf':[
            ['BOTSID', 'M', 64, 'AN'],
          ],
    'header':[
            ['BOTSID', 'M', 64, 'AN'],
            ['msg_id','C',64,'A'],
            ['msg_id2','C',64,'A'],
            ['datetime', 'C', 20, 'AN'],
            ['state', 'C', 64, 'AN'],
            ['type', 'C', 64, 'AN'],
            ['test', 'C', 64, 'AN'],
          ],
    'shipment':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['name', 'C', 64, 'AN'],
            ['desc', 'C', 64, 'AN'],
            ['manifest', 'C', 64, 'AN'],
            ['date_ship', 'C', 64, 'AN'],
            ['date_delivery', 'C', 64, 'AN'],
            ['date_delivery_type', 'C', 64, 'AN'],
            ['type', 'C', 64, 'AN'],
            ['reason', 'C', 64, 'AN'],
            ['service', 'C', 64, 'AN'],
            ['carrier', 'C', 64, 'AN'],
            ['confirmed', 'C', 64, 'AN'],
            ['buisness_type', 'C', 64, 'AN'],
          ],
    'invoice':[
            ['BOTSID', 'M', 64, 'AN'],
            ['name','C',64,'AN'],
            ['currency', 'C', 64, 'AN'],
            ['payment_term', 'C', 64, 'AN'],
          ],
    'references':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['desc', 'C', 64, 'AN'],
            ['type', 'C', 64, 'AN'],
            ['datetime', 'C', 64, 'AN'],
          ],
    'values':[
            ['BOTSID', 'M', 64, 'AN'],
            ['type','C',64,'AN'],
            ['total', 'C', 64, 'AN'],
            ['currency', 'C', 64, 'AN'],
          ],
    'partner':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['name', 'C', 64, 'AN'],
            ['street1', 'C', 64, 'AN'],
            ['street2', 'C', 64, 'AN'],
            ['city', 'C', 64, 'AN'],
            ['zip', 'C', 64, 'AN'],
            ['country', 'C', 64, 'AN'],
            ['state', 'C', 64, 'AN'],
            ['phone', 'C', 64, 'AN'],
            ['fax', 'C', 64, 'AN'],
            ['email', 'C', 64, 'AN'],
            ['language', 'C', 64, 'AN'],
            ['vat', 'C', 64, 'AN'],
          ],
    'line':[
            ['BOTSID', 'M', 64, 'AN'],
            ['id','C',64,'AN'],
            ['seq', 'C', 64, 'AN'],
            ['type', 'C', 64, 'AN'],
            ['datetime', 'C', 64, 'AN'],
            ['product', 'C', 64, 'AN'],
            ['uom_qty', 'C', 64, 'AN'],
            ['uom', 'C', 64, 'AN'],
            ['qty_real', 'C', 64, 'AN'],
            ['qty_expected', 'C', 64, 'AN'],
          ],
     }

