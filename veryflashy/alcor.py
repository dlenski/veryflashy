#!/usr/bin/env python

import argparse
import os
import sys
import logging

import humanize
from py_sg import SCSIError

from .common import bytesy, sgread as _sgread

p = argparse.ArgumentParser()
p.add_argument('-d', '--debug', action='store_true')
p.add_argument('dev', help="Path to Alcor USB flash drive (e.g. /dev/sda or /dev/sg0)")
args = p.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

fd = os.open(args.dev, os.O_RDWR | os.O_NONBLOCK)
#print('opened with flags: 0x%04x' %(os.O_RDWR | os.O_NONBLOCK))

# See
# https://github.com/tizbac/alcorhack/blob/master/commands.txt
# https://linuxehacking.ovh/2014/07/12/alcor-ufd-controller-reverse/
# https://linuxehacking.ovh/2014/07/20/alcor-ufd-controller-hacking-update-2/

def sgread(fd, cmd, bufLen, timeout_ms=None, flags=0):
    '''Bad workaround for timeout issues with this device'''
    if timeout_ms is None:
        timeout_ms = 1_000

    try:
        return _sgread(fd, cmd, bufLen, timeout_ms, flags)
    except SCSIError as exc:
        #print(exc)
        ms, hs, ds, sense, buf = exc.args
        if ms == ds == 0 and sense is None and hs == 3:
            return buf
        raise

# Initial read
print("Reading vendor info (SCSI command 82 51 01 ...):")
try:
    res = sgread(fd, bytesy('82 51 01', zpad=10), 525)
except SCSIError as exc:
    p.error("SCSI error: probably not an Alcor device")
if len(res) != 525:
    p.error("Command 82 51 01 response was not 525 bytes: probably not an Alcor device")
if res[0:2] != b"\x99\x07":
    p.error(f"Initial response did not contain 99 07 at offset 0")
if res[0xd5:0xd8] != b"PQI":
    p.error(f"Initial response did not contain string 'PQI' at offset 0xd5")

usb_vid, usb_pid = int.from_bytes(res[12:14], 'little'), int.from_bytes(res[14:16], 'little') 
print(f'  Alcor USB ID {usb_vid:04x}:{usb_pid:04x}')

# Read drive capacity (standard SCSI command)

print("Reading standard SCSI disk capacity (SCSI command 25 ...):")
res = sgread(fd, bytesy('25', zpad=14), 8)
nblks = int.from_bytes(res[:4], 'big') + 1
blksize = int.from_bytes(res[4:8], 'big')
print(f'  SCSI block size {blksize} x {nblks} = {humanize.naturalsize(blksize*nblks)}')

print("Reading vendor info (SCSI command 9a ...):")
res = sgread(fd, bytesy('9a', zpad=10), 525)
if len(res) != 525:
    p.error("Command 9a response was not 525 bytes")
nblks_be = int.from_bytes(res[0:4], 'big')
nblks_le = int.from_bytes(res[0x100:0x104], 'little')
if nblks_be != nblks_le:
    p.error('Command 9a response gives conflict big-endian and little-endian sizes')

print(f'  Alcor flash size {nblks} blocks')

# Flash ID read
print("Reading flash ID (SCSI command fa 00 ...):")
res = sgread(fd, bytesy('fa 00', zpad=8), 525)
if len(res) != 525:
    p.error("Command fa 00 response was not 525 bytes")
for ii in range(16):
    flashid = res[ii*8 : ii*8 + 6]
    if flashid != b'\xff'*6:
        flashid = '-'.join(flashid[ii:ii+1].hex() for ii in range(6))
        print(f'  Flash ID ({ii}) {flashid}')


# Unknown mystery pages of 512 bytes, lots to explore with 96NN and faNN:
# sgread(fd, bytesy('96 00', zpad=10), 512)
# sgread(fd, bytesy('fa 05', zpad=8), 512)

print('Done.')
