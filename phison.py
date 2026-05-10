#!/usr/bin/env python

import argparse
import os
import sys

import humanize
from py_sg import read as sgread, write as sgwrite, SCSIError

p = argparse.ArgumentParser()
p.add_argument('dev', help="Path to Phison USB flash drive (e.g. /dev/sda or /dev/sg0)")
args = p.parse_args()

fd = os.open(args.dev, os.O_RDWR)

# Initial read
# See https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2,
# Shmoocon talk: https://www.scribd.com/document/490018597/ShmooCon2014-Controlling-USB-Flash-Drive-Controllers,
# and transcript of talk: https://www.scribd.com/document/490018597/ShmooCon2014-Controlling-USB-Flash-Drive-Controllers

print("Reading vendor info (SCSI command 06 05 ...):")
try:
    res = sgread(fd, bytes.fromhex('06 05 00 00 00 00'), 528)
except SCSIError:
    p.error("SCSI error: probably not a Phison device")
if len(res) != 528:
    p.error("Initial response was not 528 bytes: probably not a Phison device")
if res[0xc4:0xca] != b"PhIsOn":
    p.error(f"Initial response did not contain string 'PhIsOn' at offset 0xc4")
if res[0x17a:0x17c] != b"VR":
    p.error(f"Initial response did not contain string 'VR' at offset 0x17a")

cid = res[0x17e:0x180].hex()
if cid >= '2200':
    # see https://wikidevi.wi-cat.ru/Phison#USB_Controllers
    pscid = f'PS2251-{cid[2:4]} (raw value {cid})'
else:
    pscid = f'{cid} (NOT 22xx OR 23xx)'
fwver = '.'.join(str(b) for b in res[0x94:0x97])
f1f2 = res[0x9a:0x9c].hex()

print(f'  Phison chip ID: {pscid}')
print(f'  Phison firmware version/date: {fwver}')
print(f'  Phison f1f2: {f1f2} (NOT SURE WHAT THIS IS)')
# https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2?permalink_comment_id=5610067#gistcomment-5610067
usb_vid, usb_pid = int.from_bytes(res[8:10], 'little'), int.from_bytes(res[10:12], 'little') 
print(f'  Phison USB ID {usb_vid:04x}:{usb_pid:04x}')

# Read drive capacity (standard SCSI command)

print("Reading standard SCSI disk capacity (SCSI command 25 ...):")
res = sgread(fd, bytes.fromhex('25 00 00 00 00 00 00 00 00 00 00 00 00 00'), 8)
nblks = int.from_bytes(res[:4], 'big') + 1
blksize = int.from_bytes(res[4:8], 'big')
print(f'  SCSI block size {blksize} x {nblks} = {humanize.naturalsize(blksize*nblks)}')

# 'INFO' read
# https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2

print("Reading vendor info (SCSI command 06 05 49 4e 46 4f):")
res = sgread(fd, bytes.fromhex('06 05') + b'INFO', 528)
if len(res) != 528:
    p.error("INFO response was not 528 bytes")
if res[0xc4:0xca] != b"PhIsOn":
    p.error(f"INFO response did not contain string 'PhIsOn' at offset 0xc4")
mode = res[0xac]
write_prot = res[0x131] & 1 # https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2?permalink_comment_id=5829546#gistcomment-5829546
split = int.from_bytes(res[0x1fc:0x200], 'big')
print(f'  Phison split mode {mode}, split at {split} blocks = {split*blksize} bytes') # https://wikidevi.wi-cat.ru/Phison#USB_Controllers:~:text=PS2309%20%3D%20PS2251%2D09-,Mode,-Mode%203%20(No
print(f'  Phison write-protect bit: {write_prot} (WRONG?)')

# Flash ID read
print("Reading flash ID (this will take up to 120 seconds:")
res = sgread(fd, bytes.fromhex('06 56 00 00 00 00 00 00 00 00 00 00'), 512, 120_000)
flashid = '-'.join(res[ii:ii+1].hex() for ii in range(6))
print(f'  Flash ID {flashid}')

print('Done.')

