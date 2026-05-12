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
    p = argparse.ArgumentParser()
    p.add_argument('-d', '--debug', action='store_true')
    p.add_argument('dev', help="Path to PL2530 USB flash drive (e.g. /dev/sda or /dev/sg0)")
    args = p.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    fd = os.open(args.dev, os.O_RDWR | os.O_NONBLOCK)
    try:
        probe(fd)
    except NotImplementedError as exc:
        p.error("Probably not a Phison USB NAND Flash controller: {exc.args[0]}")


def probe(fd: int):
    # Found with scsifuzz

    # Initial read
    try:
        res = sgread(fd, bytesy('f8 01', zpad=10), 512)
    except SCSIError as exc:
        raise NotImplementedError("SCSI error: probably not a PL2530 device")
    if res[0:2] != b"PL":
        raise NotImplementedError("Command a1 response did not start with PL: probably not a PL2530 device")
    print("Reading vendor info (SCSI command f8 01 ...):")

    vi = res.decode('ascii').rstrip('\0')
    print(f'  PL2530 version info: {vi!r}')

    print("Reading capacity page (SCSI command f8 02 ...):")
    try:
        res = sgread(fd, bytesy('f8 02', zpad=12), 512)
    except SCSIError as exc:
        raise NotImplementedError("Didn't get response to f8 02 command")
    nblks = int.from_bytes(res[1:5], 'big')
    print(f'  PL2503 flash size {nblks} blocks')

    return None
