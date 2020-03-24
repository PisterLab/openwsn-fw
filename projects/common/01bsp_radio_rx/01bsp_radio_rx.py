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
    t = '/dev/ttyUSB0'    
    if t.strip():
        serialport = t.strip()
    mote = mote_connect(serialport=serialport)

#============================ read ============================================

rawFrame         = []
rawFrame_decoded = []
previousFrame    = 0
frameCounter     = 0
xonxoffEscaping  = False

packet_size = 12; # default 9

while True:
    
    if iotlab_serialport:
        bytes = mote.recv(1024)
        rawFrame += [ord(b) for b in bytes]
    else:
        byte  = mote.read(1)
        rawFrame += [ord(byte)]
    
    if rawFrame[-3:]==[0xff]*3 and len(rawFrame)>=packet_size:
        
        #
        #for byte in rawFrame:
        #    if byte==XONXOFF_ESCAPE:
        #        xonxoffEscaping = True
        #    else:
        #        if xonxoffEscaping==True:
        #            rawFrame_decoded += [byte^XONXOFF_MASK]
        #            xonxoffEscaping=False
        #        elif byte!=XON and byte!=XOFF:
        #            rawFrame_decoded += [byte]

        rawFrame_decoded = rawFrame
        
        #(rxpk_len,rxpk_num,rxpk_rssi,rxpk_lqi,rxpk_crc, rxpk_freq_offset) = \
        #    struct.unpack('>BBbBBb', ''.join([chr(b) for b in rawFrame_decoded[-9 :-3]]))

        (c, m, f, rxpk_len,rxpk_num,rxpk_rssi,rxpk_lqi,rxpk_crc, rxpk_freq_offset) = \
            struct.unpack('>BBBBBbBBb', ''.join([chr(b) for b in rawFrame_decoded[-packet_size :-3]]))

        #print(rawFrame_decoded[-packet_size :-3])

        if rxpk_num == 0 or rxpk_len != 22:
            continue
        if c == 1 and m ==2 and f == 3:
            continue;

        #(rxpk_len,rxpk_num,coarse,mid,fine, rxpk_freq_offset) = \
        #    struct.unpack('>BBBBBb', ''.join([chr(b) for b in rawFrame_decoded[-9 :-3]]))

        #rxpk_buf = rawFrame_decoded[-9-rxpk_len:-9]
        #unpacked_buf = struct.unpack('>' + "B"*rxpk_len, ''.join([chr(b) for b in rxpk_buf]))
        #print unpacked_buf
            
        # debug info
        #output = 'len={0:<3} num={1:<3} rssi={2:<4} lqi={3:<3} crc={4} freq_offset={5:<4}'.format(
        #    rxpk_len,
        #    rxpk_num,
        #    rxpk_rssi,
        #    rxpk_lqi,
        #    rxpk_crc,
        #    rxpk_freq_offset
        #)

        output = 'len={0:<3} num={1:<3} rssi={2:<4} lqi={3:<3} crc={4} freq_offset={5:<4} c={6:<4} m={7:<4} f={8:<4}'.format(
            rxpk_len,
            rxpk_num,
            rxpk_rssi,
            rxpk_lqi,
            rxpk_crc,
            rxpk_freq_offset,
            c,
            m,
            f
        )

        def process_string_msg(packet_lst):
            message_lst = [chr(x) for x in packet_lst[1:]] 
            return "".join(message_lst)

        def process_freq_msg(packet_lst):
            if len(packet_lst) < 4:
                return "INVALID PACKET"
            
            coarse, mid, fine = packet_lst[1], packet_lst[2], packet_lst[3]
            return "coarse:" + str(coarse) + " mid: " + str(mid) + " fine: " + str(fine)
            
        #print "coarse:" + str(coarse) + " mid: " + str(mid) + " fine: " + str(fine)

        print output
        #print ','.join(rxpk_buf)
        #print rxpk_buf
        #print rawFrame


        #message = process_string_msg(rxpk_buf)
        #message = process_freq_msg(rxpk_buf)
    
        #print message + '\t' + output       

        with open('log.txt','a') as f:
            f.write(output+'\n')
        
        if rxpk_len>127:
            #print "ERROR: frame too long.\a"
            a = 0 # just placeholder
        else:
            if previousFrame>rxpk_num:
                output = "frameCounter={0:<3}, PDR={1}%".format(frameCounter, frameCounter*100/MAX_NUM_PACKET)
                #print output
                frameCounter  = 0
                with open('log.txt','a') as f:
                    f.write(output+'\n')

            frameCounter += 1
            previousFrame = rxpk_num
        
        rawFrame         = []
        rawFrame_decoded = []
