#!/usr/bin/env python

import argparse
import os
import sys
import logging

import humanize
from py_sg import SCSIError

from .common import bytesy, sgread

p = argparse.ArgumentParser()
p.add_argument('-d', '--debug', action='store_true')
p.add_argument('dev', help="Path to PL2530 USB flash drive (e.g. /dev/sda or /dev/sg0)")
args = p.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

fd = os.open(args.dev, os.O_RDWR | os.O_NONBLOCK)

# Found with scsifuzz

# Initial read
print("Reading vendor info (SCSI command f8 01 ...):")
try:
    res = sgread(fd, bytesy('f8 01', zpad=10), 512)
except SCSIError as exc:
    p.error("SCSI error: probably not a PL2530 device")
if res[0:2] != b"PL":
    p.error("Command a1 response did not start with PL: probably not a PL2530 device")

vi = res.decode('ascii').rstrip('\0')
print(f'  PL2530 version info: {vi!r}')

print("Reading capacity page (SCSI command f8 02 ...):")
try:
    res = sgread(fd, bytesy('f8 02', zpad=12), 512)
except SCSIError as exc:
    p.error("Didn't get response to f8 02 command")
nblks = int.from_bytes(res[1:5], 'big')
print(f'  PL2503 flash size {nblks} blocks')

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

print('Done.')
