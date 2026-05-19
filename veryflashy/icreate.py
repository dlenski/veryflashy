#!/usr/bin/env python

import logging

from py_sg import SCSIError

from .common import bytesy, sgread

logger = logging.getLogger(__name__)


def probe(fd: int):
    # Do a regular INQ and an "extended" INQ requesting 79 bytes.
    try:
        res1 = sgread(fd, bytesy('12 00 00 00 24 00'), 36)
        res2 = sgread(fd, bytesy('12 00 00 00 4f 00'), 79)
    except SCSIError as exc:
        raise NotImplementedError("SCSI error: probably not an iCreate device")
    if len(res1) != 36 or not res2.startswith(res1 + b'iCreate Technologies Corporation'):
        raise NotImplementedError("SCSI extended INQ didn't give expected result: probably not an iCreate device")
    print("Reading extended INQ (SCSI command 12 00 00 00 4f 00):")

    chip_id = res2[0x44:].decode('ascii')
    print(f"  iCreate chip ID: {chip_id!r}")

    # Use the magic vendor command to read the flash chip
    print("Reading flash ID (c2 01 90 00 00 00 00 00 80 00 69 ba)...")
    try:
        res = sgread(fd, bytesy('c2 01 90 00 00 00 00 00 80 00 69 ba'), 128)
    except SCSIError as exc:
        raise NotImplementedError("Didn't get response to flash ID command")

    flashids = []
    for ii in range(2):
        # It appears this device truly only supports 4-byte NAND flash IDs,
        # since it predates the introduction of 6-byte NAND flash IDs
        # sometime around 2010.
        # https://lists.infradead.org/pipermail/linux-mtd-cvs/2012-September/008206.html
        flashid = res[ii*4 : ii*4 + 4]
        if flashid != b'\xff'*4:
            print(f'  Flash ID ({ii}) {flashid.hex(sep="-")}')
            flashids.append(flashid)

    if flashids:
        return flashids[0]
