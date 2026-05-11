#!/usr/bin/env python

import argparse
import os
import sys
import logging

import humanize
from py_sg import SCSIError

from .common import bytesy, sgread

logger = logging.getLogger(__name__)

p = argparse.ArgumentParser()
p.add_argument('-d', '--debug', action='store_true')
p.add_argument('dev', help="Path to AppoTech USB flash drive (e.g. /dev/sda or /dev/sg0)")
args = p.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

fd = os.open(args.dev, os.O_RDWR | os.O_NONBLOCK)
#print('opened with flags: 0x%04x' %(os.O_RDWR | os.O_NONBLOCK))

# Found with scsifuzz

# Initial read
print("Reading vendor info (SCSI command a1 00 ...):")
try:
    res = sgread(fd, bytesy('a1', zpad=12), 512)
except SCSIError as exc:
    p.error("SCSI error: probably not an AppoTech device")
if res[0:2] != b"DM":
    p.error("Command a1 response did not start with DM: probably not a AppoTech device")

vi = res.decode('ascii').rstrip('\0')
print(f'  AppoTech version info: {vi!r}')

# Page 1 (?) read
# There's a lot of other USB-related info in here
print("Reading vendor info (SCSI command a1 01 ...):")
try:
    res = sgread(fd, bytesy('a1 01', zpad=12), 1024)
except SCSIError as exc:
    p.error("Didn't get response to a1 01 command")
nblks = int.from_bytes(res[8:11], 'big')
print(f'  AppoTech flash size {nblks} blocks')
usb_vid, usb_pid = int.from_bytes(res[0x2a:0x2c], 'little'), int.from_bytes(res[0x2c:0x2e], 'little')
print(f'  AppoTech USB ID {usb_vid:04x}:{usb_pid:04x}')


# Read drive capacity (standard SCSI command)

print("Reading standard SCSI disk capacity (SCSI command 25 ...):")
res = sgread(fd, bytesy('25', zpad=14), 8)
nblks = int.from_bytes(res[:4], 'big') + 1
blksize = int.from_bytes(res[4:8], 'big')
print(f'  SCSI block size {blksize} x {nblks} = {humanize.naturalsize(blksize*nblks)}')

print("Reading standard SCSI block limits (SCSI command 23 ...):")
res = sgread(fd, bytes.fromhex('23 00 00 00 00 00 00 00 00 00 00 00'), 12)
assert res[3] == 8 and len(res) == 12
nblks = int.from_bytes(res[4:8], 'big')
blksize = int.from_bytes(res[10:12], 'big')
print(f'  SCSI block size {blksize} x {nblks} = {humanize.naturalsize(blksize*nblks)}')

# Flash ID read
print("Reading flash ID (SCSI command a5 ...):")
res = sgread(fd, bytesy('a5', zpad=12), 512)
if len(res) < 8:
    p.error("Command a5 response was not >=8 bytes")
flashid = res[0:6]
flashid = '-'.join(flashid[ii:ii+1].hex() for ii in range(6))
print(f'  AppoTech Flash ID {flashid}')

print('Done.')
