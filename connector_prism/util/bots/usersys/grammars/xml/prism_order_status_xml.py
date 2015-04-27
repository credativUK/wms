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

structure=    [
    {ID:'orders',MIN:1,MAX:1,
        QUERIES:{
            'frompartner':  {'BOTSID':'orders','sender':None},
            'topartner':    {'BOTSID':'orders','receiver':None},
            },
        LEVEL:[
        {ID:'order',MIN:1,MAX:999,LEVEL:[
            {ID:'items',MIN:1,MAX:1,LEVEL:[
                {ID:'item',MIN:1,MAX:999,LEVEL:[
                    {ID:'attributes',MIN:0,MAX:1,LEVEL:[
                        {ID:'attribute',MIN:0,MAX:999},
                    ]},
                ]},
            ]},
        ]},
    ]},
]

recorddefs = {
    'envelope':[
            ['BOTSID','M',255,'A'],
          ],
    'orders':[
            ['BOTSID','M',255,'A'],
          ],
    'order':[
            ['BOTSID','M',255,'A'],

            ['orderNumber', 'M', 10, 'A'],
            ['externalDocumentRef1', 'C', 25, 'A'],
            ['externalDocumentRef2', 'C', 25, 'A'],
          ],
    'attributes':[
            ['BOTSID','M',255,'A'],
          ],
    'attribute':[
            ['BOTSID','M',255,'A'],
            ['name', 'M', 50, 'AN'],
            ['value', 'M', 99999, 'AN'],
          ],
    'items':[
            ['BOTSID','M',255,'A'],
          ],
    'item':[
            ['BOTSID','M',255,'A'],
            ['productCode', 'M', 30, 'A'],
            ['status', 'M', 10, 'A'],
            ['statusDate', 'M', 19, 'A'],
          ],
     }
 
