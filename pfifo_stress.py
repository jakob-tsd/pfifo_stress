#!/usr/bin/env python3
#
# Stress-test tool to detect reordering by pfifo_fast.
#
# Adjust RX_IF and TX_IF according to your actual interface names!

import threading
import socket
import struct
import subprocess
import os
import binascii

RX_IF="enx000ec6c4856d"
TX_IF="enx0050b616e37b"

RX_IP="200.0.0.1"
TX_IP="200.0.0.2"

DUMMY_TARGET="200.0.0.99"
PORT_NUM=2000

STRUCT_FMT=">I"

def shell(cmd):
	subprocess.check_call(cmd, shell=True)

def setup_network():
	# RX
	shell("ip addr flush dev %s" % (RX_IF, ))
	shell("ip addr add %s/24 dev %s" % (RX_IP, RX_IF))
	shell("ip link set dev %s promisc on" % (RX_IF,))
	shell("ip link set dev %s up" % (RX_IF,))
	shell("mii-tool %s -F 10baseT-FD" % (RX_IF,))

	# TX
	shell("ip addr flush dev %s" % (TX_IF,))
	shell("ip addr add %s/24 dev %s" % (TX_IP, TX_IF))
	shell("ip link set dev %s up" % (TX_IF,))
	shell("mii-tool %s -F 10baseT-FD" % (TX_IF,))

	shell("arp -s %s 11:22:33:44:55:66" % (DUMMY_TARGET,))

def tx_thread():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	s.bind((TX_IP,PORT_NUM))
	i = 0
	tx_ready.set()
	while True:
		data = struct.pack(STRUCT_FMT, i)
		s.sendto(data, (DUMMY_TARGET, PORT_NUM))
		i += 1

setup_network()
tx_ready = threading.Event()
t=threading.Thread(target=tx_thread, daemon=True)
t.start()
tx_ready.wait()

# create an INET, raw socket
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
s.bind((RX_IF, 3))

last = 0

# Receive packets and check counter
while True:
	data = s.recvfrom(65565)[0]
	if len(data) != 46:
		continue
	# Counter is the last 4 bytes
	ctr = struct.unpack(STRUCT_FMT, data[-4:])[0]
	if last+1 != ctr:
		print("expected ctr 0x%x, received 0x%x" % (last+1, ctr))
	last = ctr
