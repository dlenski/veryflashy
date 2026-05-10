#!/usr/bin/env python

import argparse
import os
import py3_sg
from py3_sg import read_as_bin_str as sgread

p = argparse.ArgumentParser()
p.add_argument('dev', help="Path to Phison USB flash drive (e.g. /dev/sda or /dev/sg0)")
args = p.parse_args()

fd = os.open(args.dev, os.O_RDWR)

# Initial read
res = sgread(fd, bytes.fromhex('06 05 00 00 00 00 00 00 01'), 1024)
if len(res) != 528:
    p.error("Initial response was not 528 bytes (see https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2)")
if res[0xc4:0xca] != b"PhIsOn":
    p.error(f"Initial response did not contain string 'PhIsOn' at offset 0xc4")
if res[0x17a:0x17c] != b"VR":
    p.error(f"Initial response did not contain string 'VR' at offset 0x17a")
cid = res[0x17e:0x180].hex()
fwver = map(str, res[0x94:0x97])
print(f'Phison chip ID: PS{cid}')
print(f'Phison firmware version: {".".join(fwver)}')
usb_vid, usb_pid = int.from_bytes(res[8:10], 'little'), int.from_bytes(res[10:12], 'little') # https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2?permalink_comment_id=5610067#gistcomment-5610067
print(f'Phison USB ID {usb_vid:x}:{usb_pid:x}')

# Read capacity (standard SCSI command)
res = sgread(fd, bytes.fromhex('25 00 00 00 00 00 00 00 00 00 00 00 00 00'), 8)
nblks, blksize = int.from_bytes(res[:4]), int.from_bytes(res[4:8])
print(f'SCSI block size {blksize} x {nblks} = {nblks*blksize} bytes')

# 'INFO' read
res = sgread(fd, bytes.fromhex('06 05') + b'INFO', 1024)
if len(res) != 528:
    p.error("INFO response was not 528 bytes (see https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2)")
if res[0xc4:0xca] != b"PhIsOn":
    p.error(f"INFO response did not contain string 'PhIsOn' at offset 0xc4")
mode = res[0xac]
write_prot = res[0x131] & 1 # https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2?permalink_comment_id=5829546#gistcomment-5829546
split = int.from_bytes(res[0x1fc:0x200])
print(f'Phison split mode {mode}, split at {split} blocks = {split*blksize} bytes') # https://wikidevi.wi-cat.ru/Phison#USB_Controllers:~:text=PS2309%20%3D%20PS2251%2D09-,Mode,-Mode%203%20(No
print(f'Phison write-protect bit: {write_prot}')

# Flash ID read
res = sgread(fd, bytes.fromhex('06 56 00 00 00 00 00 00 00 00 00 00'), 1024, 5_000)
flashid = res[:6].hex()
print(f'Flash ID {flashid}')

#print(res)

