#!/usr/bin/env python

import argparse
import os
import sys
import logging

import humanize
from py_sg import SCSIError

from .common import bytesy, sgread as _sgread


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


def probe(fd: int):
    # See
    # https://github.com/tizbac/alcorhack/blob/master/commands.txt
    # https://linuxehacking.ovh/2014/07/12/alcor-ufd-controller-reverse/
    # https://linuxehacking.ovh/2014/07/20/alcor-ufd-controller-hacking-update-2/

    # Initial read
    try:
        res = sgread(fd, bytesy('82 51 01', zpad=10), 525)
    except SCSIError as exc:
        raise NotImplementedError("Initial command failed") from exc
    if len(res) != 525:
        raise NotImplementedError("Command 82 51 01 response was not 525 bytes: probably not an Alcor device")
    if res[0:2] != b"\x99\x07":
        raise NotImplementedError(f"Initial response did not contain 99 07 at offset 0")
    if res[0xd5:0xd8] != b"PQI":
        raise NotImplementedError(f"Initial response did not contain string 'PQI' at offset 0xd5")
    print("Reading vendor info (SCSI command 82 51 01 ...):")

    usb_vid, usb_pid = int.from_bytes(res[12:14], 'little'), int.from_bytes(res[14:16], 'little')
    print(f'  Alcor USB ID {usb_vid:04x}:{usb_pid:04x}')

    print("Reading vendor info (SCSI command 9a ...):")
    res = sgread(fd, bytesy('9a', zpad=10), 525)
    if len(res) != 525:
        raise NotImplementedError("Command 9a response was not 525 bytes")
    nblks_be = int.from_bytes(res[0:4], 'big')
    nblks_le = int.from_bytes(res[0x100:0x104], 'little')
    if nblks_be != nblks_le:
        raise NotImplementedError('Command 9a response gives conflict big-endian and little-endian sizes')
    print(f'  Alcor flash size {nblks} blocks')

    # Flash ID read
    print("Reading flash ID (SCSI command fa 00 ...):")
    res = sgread(fd, bytesy('fa 00', zpad=8), 525)
    if len(res) != 525:
        raise NotImplementedError("Command fa 00 response was not 525 bytes")

    flashids = []
    for ii in range(16):
        flashid = res[ii*8 : ii*8 + 6]
        if flashid != b'\xff'*6:
            print(f'  Flash ID ({ii}) {flashid.hex(sep="-")}')
            flashids.append(flashid)

    if flashids:
        return flashids[0]

    # Unknown mystery pages of 512 bytes, lots to explore with 96NN and faNN:
    # sgread(fd, bytesy('96 00', zpad=10), 512)
    # sgread(fd, bytesy('fa 05', zpad=8), 512)
