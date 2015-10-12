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

def ta_infocontent(ta_info,*args,**kwargs):
    ta_info['add_crlfafterrecord_sep'] = ''
    ta_info['reserve'] = 'U'
    ta_info['ISA05'] = 'ZZ'
    ta_info['ISA07'] = 'ZZ'
    # FIXME: Not the best way to write this - if we are receiving a message then
    # we do not want a confirmation when sending out a confirmation
    if 'inbound' in ta_info['idroute']:
        ta_info['ISA14'] = '0'
    # FIXME: Not the best way to write this - if the route is for testing then
    # we should set the test flag acordingly
    if 'test' in ta_info['idroute']:
        ta_info['ISA15'] = 'T'

def envelopecontent(ta_info, out, *args, **kwargs):
    pass

