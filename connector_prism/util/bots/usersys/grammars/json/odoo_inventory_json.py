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
{ID:'inventory',MIN:1,MAX:999999,
    QUERIES:{
        'frompartner':  ({'BOTSID':'messages'},{'BOTSID':'header','partner_name':None}),
        'topartner':    ({'BOTSID':'messages'},{'BOTSID':'header','partner_name':None}),
        'reference':    ({'BOTSID':'messages'},{'BOTSID':'header','msg_id':None}),
        'testindicator':({'BOTSID':'messages'},{'BOTSID':'header','test':None})},
    LEVEL:[
        {ID:'header',MIN:0,MAX:1},
        {ID:'partner',MIN:0,MAX:1},
        {ID:'inventory_line',MIN:0,MAX:999999},
        ]},
]

recorddefs = {
    'inventory':[
            ['BOTSID', 'M', 64, 'AN'],
          ],
    'header':[
            ['BOTSID', 'M', 64, 'AN'],
            ['msg_id','C',64,'A'],
            ['datetime', 'C', 20, 'AN'],
            ['partner_name', 'C', 64, 'AN'],
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
    'inventory_line':[
            ['BOTSID', 'M', 64, 'AN'],
            ['product','M',64,'AN'],
            ['product_article_no', 'C', 64, 'AN'],
            ['product_other', 'C', 64, 'AN'],
            ['product_other_type', 'C', 64, 'AN'],
            ['qty_total', 'C', 64, 'N'],
            ['qty_incoming', 'C', 64, 'N'],
            ['qty_available', 'M', 64, 'N'],
            ['qty_outgoing', 'C', 64, 'N'],
            ['qty_outgoing_available', 'C', 64, 'N'],
            ['qty_outgoing_future', 'C', 64, 'N'],
            ['datetime', 'M', 64, 'AN'],
          ],
     }

