#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import struct
import socket
try:
   import serial
except ImportError:
   pass

banner  = []
banner += [""]
banner += [" ___                 _ _ _  ___  _ _ "]
banner += ["| . | ___  ___ ._ _ | | | |/ __>| \ |"]
banner += ["| | || . \/ ._>| ' || | | |\__ \|   |"]
banner += ["`___'|  _/\___.|_|_||__/_/ <___/|_\_|"]
banner += ["     |_|                  openwsn.org"]
banner += [""]
banner  = '\n'.join(banner)
print banner

XOFF           = 0x13
XON            = 0x11
XONXOFF_ESCAPE = 0x12
XONXOFF_MASK   = 0x10

MAX_NUM_PACKET = 256 

def mote_connect(motename=None , serialport= None, baudrate='115200'):
    try:
        if (motename):
            mote = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            mote.connect((motename,20000))
        else:
            mote = serial.Serial(serialport, baudrate)
        return mote
    except Exception as err:
        print "{0}".format(err)
        raw_input('Press Enter to close.')
        sys.exit(1)
    

#============================ configuration and connection ===================================

iotlab_serialport = False
motename = 'wsn430-35'
serialport = 'COM10'
mote = None

#t = raw_input('Are you running on IoT-LAB nodes ? (Y|N): ')
t = 'n'
if  (not t.strip() or t.strip() in ['1','yes','y','Y']):
    t = raw_input('Enter mote name ? (e.g. {0}): '.format(motename))
    if t.strip():
        motename = t.strip()
    archi = motename.split('-')
    assert len(archi) == 2
    assert archi[0] in ['wsn430', 'a8', 'm3'] 
    if (archi[0] != 'a8'):
        iotlab_serialport = True
        mote = mote_connect(motename=motename)
    else:
        mote = mote_connect(serialport='/dev/ttyA8_M3', baudrate='500000')
    
else:
    #t = raw_input('Enter serial port name (e.g. {0}): '.format(serialport))    
    t = '/dev/ttyUSB1'    
    if t.strip():
        serialport = t.strip()
    mote = mote_connect(serialport=serialport)

#============================ read ============================================

CRC_LEN = 2

rawFrame         = []
rawFrame_decoded = []
previousFrame    = 0
frameCounter     = 0
xonxoffEscaping  = False

scum_pkt_size = 4 + CRC_LEN
additional_pkt_info_size = 5 # for rxpk_len,rxpk_rssi,rxpk_lqi,rxpk_crc, rxpk_freq_offset
neg_1_size = 3 # data sent by uart has -1, -1, -1 sent once information is fully sent. This is an end flag.
uart_pkt_size = scum_pkt_size + additional_pkt_info_size + neg_1_size

while True:
    
    if iotlab_serialport:
        bytes = mote.recv(1024)
        rawFrame += [ord(b) for b in bytes]
    else:
        byte  = mote.read(1)
        rawFrame += [ord(byte)]
    
    if rawFrame[-neg_1_size:]==[0xff]*neg_1_size and len(rawFrame)>=uart_pkt_size:
        rawFrame_decoded = rawFrame

        to_decode = rawFrame_decoded[-uart_pkt_size :-neg_1_size]
        #print(to_decode)

        # packet items 0-21, rxpk_len,rxpk_rssi,rxpk_lqi,rxpk_crc, rxpk_freq_offset
        uart_rx = struct.unpack('>' + 'B' * scum_pkt_size +  'BbBBb', ''.join([chr(b) for b in to_decode]))

        pkt = uart_rx[0:scum_pkt_size]

        (rxpk_len,rxpk_rssi,rxpk_lqi,rxpk_crc, rxpk_freq_offset) = uart_rx[scum_pkt_size:scum_pkt_size + additional_pkt_info_size]

        if rxpk_len != scum_pkt_size:
            continue

        output = 'len={0:<3} rssi={1:<3} lqi={2:<1} crc={3:<1} freq_offset={4:<4}'.format(
            rxpk_len,
            rxpk_rssi,
            rxpk_lqi,
            rxpk_crc,
            rxpk_freq_offset,
        )

        if pkt[1] == 1 and pkt[2] == 2 and pkt[3] == 4:
            continue;


        output += "pkt " + "0-" + str(scum_pkt_size - 1) + ": "

        for i in range(scum_pkt_size - CRC_LEN):
            output += '{0:<3}'.format(pkt[i]) + "| "

        print output
        
#        if rxpk_len>127:
            #print "ERROR: frame too long.\a"
#            a = 0 # just placeholder
#        else:
#            if previousFrame>rxpk_num:
#                output = "frameCounter={0:<3}, PDR={1}%".format(frameCounter, frameCounter*100/MAX_NUM_PACKET)
                #print output
#                frameCounter  = 0
#                with open('log.txt','a') as f:
#                    f.write(output+'\n')

#            frameCounter += 1
#            previousFrame = rxpk_num
        
        rawFrame         = []
        rawFrame_decoded = []
