#!/usr/bin/env python

import argparse
import os
import sys
import logging

import humanize
from py_sg import SCSIError

from .common import bytesy, sgread

logger = logging.getLogger(__name__)


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
