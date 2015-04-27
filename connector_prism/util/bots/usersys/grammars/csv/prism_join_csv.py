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
        'field_sep': ',',
        'quote_char':   '"',
        'charset':  "iso-8859-1",
        'noBOTSID': True,
        'skip_firstline': True,
        'envelope':'csvheader',
        'merge': False,
        'forcequote': 0,
        }

structure=    [
    {ID:'LINE',MIN:1,MAX:1000000}
    ]

recorddefs = {
    'LINE':[
            ['BOTSID','C',4,'A'],
            ['itemID', 'C', 30, 'A'],
            ['poNumber', 'C', 10, 'A'],
          ],
    }
