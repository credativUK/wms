#mapping-script
import bots.transform as transform


def main(inn,out):
    #sender, receiver is correct via QUERIES in grammar. 
    out.put({'BOTSID':'ST','ST01':'856','ST02':out.ta_info['reference'].zfill(4)})
    
    out.put({'BOTSID':'ST'},{'BOTSID':'BSN','BSN01':'00'})
    out.put({'BOTSID':'ST'},{'BOTSID':'BSN',
                             'BSN02':inn.get({'BOTSID': 'picking'}, {'BOTSID': 'header', 'docnum': None}),
                             'BSN03':transform.datemask(inn.get({'BOTSID': 'picking'}, {'BOTSID': 'header', 'date_msg': None}),'CCYY-MM-DD HH:mm:ss','CCYYMMDD'),
                             'BSN04':transform.datemask(inn.get({'BOTSID': 'picking'}, {'BOTSID': 'header', 'date_msg': None}),'CCYY-MM-DD HH:mm:ss','HHmm'),
                             'BSN05':'0001'})        #0001: Shipment, Order, Packaging, Item

    #***********************************************************************************************
    #shipment level*********************************************************************************
    hlcounter = 1       #HL segments have sequentail count
    shipment = out.putloop({'BOTSID':'ST'},{'BOTSID':'HL','HL01':hlcounter,'HL03':'S'})
    currentshipment = hlcounter     #remember the current counter, as child-HL segments have to point to this shipment
    hlcounter += 1

    total_ordered_qty = 0

    pinn = inn.getloop({'BOTSID': 'picking'}, {'BOTSID': 'pickings'})
    for pick in pinn:
        shipment.put({'BOTSID':'HL'},{'BOTSID':'DTM',
                                      'DTM01':'011',
                                      'DTM02':transform.datemask(pick.get({'BOTSID': 'pickings', 'ship_date': None}),'CCYY-MM-DD HH:mm:ss','CCYYMMDD'),
                                      'DTM03':transform.datemask(pick.get({'BOTSID': 'pickings', 'ship_date': None}),'CCYY-MM-DD HH:mm:ss','HHmm'),
                                      'DTM04':'MS'})

        ordernode = out.putloop({'BOTSID':'ST'},{'BOTSID':'HL','HL01':hlcounter,'HL02':currentshipment,'HL03':'O'})
        currentorder = hlcounter
        hlcounter += 1
        ordernode.put({'BOTSID':'HL'},{'BOTSID':'PRF',
                                       'PRF01':pick.get({'BOTSID': 'pickings', 'order': None})})
        ordernode.put({'BOTSID':'HL'},{'BOTSID':'PRF',
                                       'PRF04':transform.datemask(pick.get({'BOTSID': 'pickings', 'order_date': None}),'CCYY-MM-DD HH:mm:ss','CCYYMMDD')})

        out.put({'BOTSID':'ST'},{'BOTSID':'HL','HL01':hlcounter,'HL02':currentorder,'HL03':'P'})
        currentpack = hlcounter
        hlcounter += 1

        #***************************************************************************************************
        #line/article level*********************************************************************************
        #loop over all lines that have this sscc
        plines = pick.getloop({'BOTSID': 'pickings'}, {'BOTSID': 'line'})
        for pline in plines:
            itemnode = out.putloop({'BOTSID':'ST'},{'BOTSID':'HL','HL01':hlcounter,'HL02':currentpack,'HL03':'I'})
            hlcounter += 1
            itemnode.put({'BOTSID':'HL'},{'BOTSID':'LIN','LIN01':pline.get({'BOTSID':'line','seq':None})})
            itemnode.put({'BOTSID':'HL'},{'BOTSID':'LIN','LIN02':'SK','LIN03':pline.get({'BOTSID':'line','product_sku':None})})
            ordered_qty = pline.get({'BOTSID':'line','ordered_qty':None})
            total_ordered_qty += ordered_qty
            itemnode.put({'BOTSID':'HL'},{'BOTSID':'SN1',
                                          'SN101':pline.get({'BOTSID':'line','seq':None}),
                                          'SN102':pline.get({'BOTSID':'line','ship_qty':None}),
                                          'SN103':'EA',
                                          'SN105':ordered_qty,
                                          'SN106':'EA'})

    out.put({'BOTSID':'ST'},{'BOTSID':'CTT',
                             'CTT01':out.getcountoccurrences({'BOTSID':'LIN'}),
                             'CTT01':total_ordered_qty})
    out.put({'BOTSID':'ST'},{'BOTSID':'SE','SE01':out.getcount()+1,'SE02':out.ta_info['reference'].zfill(4)})  #SE01: bots counts the segments produced in the X12 message.
