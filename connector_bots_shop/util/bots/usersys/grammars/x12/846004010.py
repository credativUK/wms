from bots.botsconfig import *
from records004010 import recorddefs

syntax = { 
        'functionalgroup'    :  'SH',
        }

structure = [
{ID: 'ST', MIN: 1, MAX: 1, LEVEL: [
    {ID: 'BIA', MIN: 1, MAX: 1},
    {ID: 'REF', MIN: 0, MAX: 10},
    {ID: 'LIN', MIN: 1, MAX: 200000, LEVEL: [
        {ID: 'QTY', MIN: 1, MAX: 99999},
    ]},
    {ID: 'CTT', MIN: 0, MAX: 1},
    {ID: 'SE', MIN: 1, MAX: 1},
]}
]
