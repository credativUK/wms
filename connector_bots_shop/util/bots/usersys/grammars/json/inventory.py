# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2015 credativ Ltd
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

from bots.botsconfig import *

syntax = { 
        'indented': True,
    }

structure = [
{ID:'inventory',MIN:1,MAX:1,
    QUERIES:{
        'frompartner':  ({'BOTSID':'inventory'},{'BOTSID':'header','partner_from':None}),
        'topartner':    ({'BOTSID':'inventory'},{'BOTSID':'header','partner_to':None}),
        'testindicator':({'BOTSID':'inventory'},{'BOTSID':'header','test':None})},
    LEVEL:[
        {ID:'header',MIN:0,MAX:1},
        {ID:'products',MIN:0,MAX:999999},
        ]},
]

recorddefs = {
    'inventory':[
            ['BOTSID', 'M', 64, 'AN'],
          ],
    'header':[
            ['BOTSID', 'M', 64, 'AN'],
            ['partner_to', 'C', 20, 'AN'],
            ['partner_from', 'C', 64, 'AN'],
            ['date_msg', 'C', 64, 'AN'],
          ],
    'products':[
            ['BOTSID', 'M', 64, 'AN'],
            ['product_sku','C',48,'AN'],
            ['quantity', 'C', 64, 'AN'],
          ],
     }

