#!/usr/bin/env python

import argparse
import os
import sys
import logging

import humanize
from py_sg import SCSIError

from .common import bytesy, sgread

logger = logging.getLogger(__name__)

def main():
    logger = logging.getLogger(__name__)

    p = argparse.ArgumentParser()
    p.add_argument('-d', '--debug', action='store_true')
    p.add_argument('dev', help="Path to Phison USB flash drive (e.g. /dev/sda or /dev/sg0)")
    args = p.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    fd = os.open(args.dev, os.O_RDWR)
    try:
        probe(fd)
    except NotImplementedError as exc:
        p.error("Probably not a Phison USB NAND Flash controller: {exc.args[0]}")

    
def probe(fd: int) -> None:
    # Initial read
    # See https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2,
    # Shmoocon talk: https://www.scribd.com/document/490018597/ShmooCon2014-Controlling-USB-Flash-Drive-Controllers,
    # and transcript of talk: https://www.scribd.com/document/490018597/ShmooCon2014-Controlling-USB-Flash-Drive-Controllers

    try:
        res = sgread(fd, bytesy('06 05', zpad=6), 528)
    except SCSIError as exc:
        raise NotImplementedError("Initial command failed") from exc
    if len(res) != 528:
        raise NotImplementedError("Initial response was not 528 bytes")
    if res[0xc4:0xca] != b"PhIsOn":
        raise NotImplementedError(f"Initial response did not contain string 'PhIsOn' at offset 0xc4")
    if res[0x17a:0x17c] != b"VR":
        raise NotImplementedError(f"Initial response did not contain string 'VR' at offset 0x17a")
    print("Reading vendor info (SCSI command 06 05 ...):")

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

    # 'INFO' read
    # https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2

    print("Reading vendor info (SCSI command 06 05 49 4e 46 4f):")
    res = sgread(fd, bytesy('06 05', b'INFO'), 528)
    if len(res) != 528:
        raise NotImplementedError("INFO response was not 528 bytes")
    if res[0xc4:0xca] != b"PhIsOn":
        raise NotImplementedError(f"INFO response did not contain string 'PhIsOn' at offset 0xc4")
    mode = res[0xac]
    write_prot = res[0x131] & 1 # https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2?permalink_comment_id=5829546#gistcomment-5829546
    split = int.from_bytes(res[0x1fc:0x200], 'big')
    print(f'  Phison split mode {mode}, split at {split} blocks')  # https://wikidevi.wi-cat.ru/Phison#USB_Controllers:~:text=PS2309%20%3D%20PS2251%2D09-,Mode,-Mode%203%20(No
    print(f'  Phison write-protect bit: {write_prot} (UNRELIABLE?)')

    # Flash ID read
    print("Reading flash ID (06 56), this can take a while:")
    res = sgread(fd, bytesy('06 56', zpad=12), 512, 120_000)
    flashid = res[0:6]
    print(f'  Flash ID {flashid.hex(sep="-")}')

    # There's more stuff in 06 05 52 51 0 0 (06 05 'R' 'A')

    return flashid
