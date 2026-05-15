#!/usr/bin/env python

import argparse
import os
import sys
import logging

import humanize
from py_sg import SCSIError

from .common import bytesy, sgread

logger = logging.getLogger(__name__)


def probe(fd: int) -> None:
    # Found with scsifuzz

    # Initial read
    try:
        res = sgread(fd, bytesy('a1', zpad=12), 512)
    except SCSIError as exc:
        raise NotImplementedError("Initial command failed") from exc
    if res[0:2] != b"DM":
        raise NotImplementedError("Command a1 response did not start with DM")
    print("Reading vendor info (SCSI command a1 00 ...):")

    vi = res.decode('ascii').rstrip('\0')
    print(f'  AppoTech version info: {vi!r}')

    # Page 1 (?) read
    # There's a lot of other USB-related info in here
    print("Reading vendor info (SCSI command a1 01 ...):")
    try:
        res = sgread(fd, bytesy('a1 01', zpad=12), 1024)
    except SCSIError as exc:
        raise NotImplementedError("Didn't get response to a1 01 command") from exc
    nblks_be = int.from_bytes(res[8:11], 'big')
    nblks_le = int.from_bytes(res[0x182:0x186], 'little')
    if nblks_be != nblks_le:
        raise NotImplementedError('Command 9a response gives conflicting big-endian and little-endian sizes')
    print(f'  AppoTech flash size {nblks_le} blocks')
    usb_vid, usb_pid = int.from_bytes(res[0x2a:0x2c], 'little'), int.from_bytes(res[0x2c:0x2e], 'little')
    print(f'  AppoTech USB ID {usb_vid:04x}:{usb_pid:04x}')

    # Flash ID read
    print("Reading flash ID (SCSI command a5 ...):")
    res = sgread(fd, bytesy('a5', zpad=12), 512)
    if len(res) < 8:
        raise NotImplementedError("Command a5 response was not >=8 bytes")
    flashid = res[0:6]
    print(f'  Flash ID {flashid.hex(sep="-")}')

    return flashid
