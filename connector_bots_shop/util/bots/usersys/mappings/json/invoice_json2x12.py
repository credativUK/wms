#mapping-script
import bots.transform as transform

def main(inn,out):
    #sender, receiver is correct via QUERIES in grammar. 
    out.put({'BOTSID':'ST','ST01':'810','ST02':out.ta_info['reference'].zfill(4)})
    
    out.put({'BOTSID':'ST'},{'BOTSID':'BIG','BIG01':transform.datemask(inn.get({'BOTSID':'message','docdtm':None}),'CCYY-MM-DD HH:mm','CCYYMMDD')})
    out.put({'BOTSID':'ST'},{'BOTSID':'BIG','BIG02':inn.get({'BOTSID':'message','docnum':None})})
    out.put({'BOTSID':'ST'},{'BOTSID':'BIG','BIG04':inn.get({'BOTSID':'message','ordernumber':None})})
    
    # DTM01:011 is "ship date"
    out.put({'BOTSID':'ST'},{'BOTSID':'DTM','DTM01':'011','DTM02':transform.datemask(inn.get({'BOTSID':'message','deldtm':None}),'CCYY-MM-DD HH:mm','CCYYMMDD')})

    #loop over partys
    for party in inn.getloop({'BOTSID':'message'},{'BOTSID':'partys'},{'BOTSID':'party'}): 
        pou = out.putloop({'BOTSID':'ST'},{'BOTSID':'N1'})
        pou.put({'BOTSID':'N1','N101':party.get({'BOTSID':'party','qual':None})})
        pou.put({'BOTSID':'N1','N102':party.get({'BOTSID':'party','name1':None})})
        pou.put({'BOTSID':'N1'},{'BOTSID':'N2','N201':party.get({'BOTSID':'party','name2':None})})
        pou.put({'BOTSID':'N1'},{'BOTSID':'N3','N301':party.get({'BOTSID':'party','address1':None})})
        pou.put({'BOTSID':'N1'},{'BOTSID':'N3','N302':party.get({'BOTSID':'party','address2':None})})
        pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N401':party.get({'BOTSID':'party','city':None})})
        pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N402':party.get({'BOTSID':'party','state':None})})
        pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N403':party.get({'BOTSID':'party','pcode':None})})
        pou.put({'BOTSID':'N1'},{'BOTSID':'N4','N404':party.get({'BOTSID':'party','country':None})})

    #loop over lines***************************************
    for lin in inn.getloop({'BOTSID':'message'},{'BOTSID':'lines'},{'BOTSID':'line'}): 
        lou = out.putloop({'BOTSID':'ST'},{'BOTSID':'IT1'}) 
        lou.put({'BOTSID':'IT1','IT101':lin.get({'BOTSID':'line','linenum':None})})
        lou.put({'BOTSID':'IT1','IT103':'EA','IT102':lin.get({'BOTSID':'line','invqua':None})})
        lou.put({'BOTSID':'IT1','IT104':lin.get({'BOTSID':'line','price':None})})
        lou.put({'BOTSID':'IT1','IT106':'SK','IT107':lin.get({'BOTSID':'line','suart':None})})
        lou.put({'BOTSID':'IT1','IT108':'SK','IT109':lin.get({'BOTSID':'line','gtin':None})})
        lou.put({'BOTSID':'IT1','IT110':'SK','IT111':lin.get({'BOTSID':'line','byart':None})})

            
    out.put({'BOTSID':'ST'},{'BOTSID':'TDS','TDS01':inn.get({'BOTSID':'message','totalinvoiceamount':None})})  
    
    out.put({'BOTSID':'ST'},{'BOTSID':'ISS','ISS02':'EA','ISS01':out.getcountsum({'BOTSID':'ST'},{'BOTSID':'IT1','IT102':None}) })  #bots counts total Number of Units Shipped 
    out.put({'BOTSID':'ST'},{'BOTSID':'CTT','CTT01':out.getcountoccurrences({'BOTSID':'ST'},{'BOTSID':'IT1'}) }) #bots counts number of line items/IT1 segments 
    out.put({'BOTSID':'ST'},{'BOTSID':'SE','SE01':out.getcount()+1,'SE02':out.ta_info['reference'].zfill(4)})  #SE01: bots counts the segments produced in the X12 message.
