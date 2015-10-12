#mapping-script
import bots.botslib as botslib
import bots.transform as transform
from bots.botsconfig import *

def main(inn,out):
     transform.inn2out(inn,out)          #997 is 'copied' as output, gets formatted as xmlnocheck)
     reference = inn.get({'BOTSID':'ST'},{'BOTSID':'AK1','AK102':None})
     #~ print reference,inn.ta_info['frompartner'],inn.ta_info['topartner']
     botslib.changeq('''UPDATE ta
                        SET   confirmed=%(confirmed)s, confirmidta=%(confirmidta)s
                        WHERE reference=%(reference)s
                        AND   status=%(status)s
                        AND   confirmasked=%(confirmasked)s
                        AND   confirmtype=%(confirmtype)s
                        AND   frompartner=%(frompartner)s
                        AND   topartner=%(topartner)s
                        ''',
                         {'status':MERGED,'reference':reference,'confirmed':True,'confirmtype':'ask-x12-997','confirmidta':inn.ta_info['idta_fromfile'],
                         'confirmasked':True,'frompartner':inn.ta_info['topartner'],'topartner':inn.ta_info['frompartner']})
