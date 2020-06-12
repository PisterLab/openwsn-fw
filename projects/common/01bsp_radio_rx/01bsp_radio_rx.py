#!/usr/bin/env python
# -*- coding: utf-8 -*-

# COMMAND LINE ARGS SPECIFICATION
# Example format: python 01bsp_radio_rx.py arg1 arg2
# arg1 = serial port path.
#   Ex: MacOS: '/dev/tty.usbserial-14147301'
#   Ex: Linux: '/dev/ttyUSB1'
#   Ex: Windows: 'COM1'
# arg2 = way of interpreting the encoding of the output
#   Potential values
#       'ASCII' : converts received values to ASCII format and will display entire packet as continuous message 
#       'RAW'   : displays packet contents directly as it is received

import sys
import struct
import socket
import platform
from datetime import datetime
import serial

banner  = []
banner += [""]
banner += [" ___                 _ _ _  ___  _ _ "]
banner += ["| . | ___  ___ ._ _ | | | |/ __>| \ |"]
banner += ["| | || . \/ ._>| ' || | | |\__ \|   |"]
banner += ["`___'|  _/\___.|_|_||__/_/ <___/|_\_|"]
banner += ["     |_|                  openwsn.org"]
banner += [""]
banner  = '\n'.join(banner)
print(banner)

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

# read in the command line args
all_args = sys.argv[1:] # removes arg that is just the name of this Python file

if len(all_args) != 2:
    print('wrong number of command line args. see the top of this python file for usage specification')
    quit()

mote = mote_connect(serialport=all_args[0])
encoding_mode = all_args[1]

if encoding_mode != 'ASCII' and encoding_mode != 'RAW':
    print('encoding specified is unrecognized')
    quit()

#============================ read ============================================

CRC_LEN = 2

rawFrame         = []
rawFrame_decoded = []
previousFrame    = 0
frameCounter     = 0
xonxoffEscaping  = False

scum_pkt_size = 40 + CRC_LEN
additional_pkt_info_size = 5 # for rxpk_len,rxpk_rssi,rxpk_lqi,rxpk_crc, rxpk_freq_offset
neg_1_size = 3 # data sent by uart has -1, -1, -1 sent once information is fully sent. This is an end flag.
uart_pkt_size = scum_pkt_size + additional_pkt_info_size + neg_1_size

while True:
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

        output = datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3] + ' '

        output += 'len={0:<3} rssi={1:<3} lqi={2:<1} crc={3:<1} freq_offset={4:<4}'.format(
            rxpk_len,
            rxpk_rssi,
            rxpk_lqi,
            rxpk_crc,
            rxpk_freq_offset,
        )

        output += "pkt " + "0-" + str(scum_pkt_size - 1) + ": "

        for i in range(scum_pkt_size - CRC_LEN):
            if encoding_mode == 'ASCII':
                output += chr(pkt[i])
            elif encoding_mode == 'RAW':
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
