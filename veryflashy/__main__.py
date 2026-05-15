#!/usr/bin/env python

import argparse
import csv
import os
import logging
from pathlib import Path
from importlib import import_module

import humanize

from .common import bytesy, sgread
from . import fdnext
models = {n: import_module(name='.'+n, package=__package__)
          for n in ('phison', 'appotech', 'alcor', 'pl2530')}

logger = logging.getLogger(__name__)

def main():
    p = argparse.ArgumentParser(description='Identifies and inspects USB NAND flash drive controllers.')
    p.add_argument('-m', '--model', choices=models.keys(), help=f'Flash controller type, if already known (one of {", ".join(models)})')
    p.add_argument('-l', '--lookup', action='store_true', help=f'Look up information about NAND flash chip IDs online (from {fdnext.FDNEXT_WEB_URL})')
    p.add_argument('dev', help="Path to USB flash drive (e.g. /dev/sda or /dev/sg0)")
    p.add_argument('-d', '--debug', default=0, action='count', help='Increase debug logging verbosity (-dd will show all commands and responses sent to the device)')
    args = p.parse_args()

    if args.debug > 1:
        logging.basicConfig(level=logging.DEBUG)
    elif args.debug:
        logging.basicConfig(level=logging.INFO)

    fd = os.open(args.dev, os.O_RDWR | os.O_NONBLOCK)

    print("Reading standard SCSI disk capacity (SCSI command 25 ...):")
    res = sgread(fd, bytesy('25', zpad=14), 8)
    nblks = int.from_bytes(res[:4], 'big') + 1
    blksize = int.from_bytes(res[4:8], 'big')
    print(f'  SCSI block size {blksize} x {nblks} = {humanize.naturalsize(blksize*nblks)}')

    print("Reading standard SCSI block limits (SCSI command 23 ...):")
    res = sgread(fd, bytesy('23', zpad=12), 12)
    if len(res) >= 12 and res[3] >= 8:
        nblks = int.from_bytes(res[4:8], 'big')
        blksize = int.from_bytes(res[10:12], 'big')
        print(f'  SCSI block size {blksize} x {nblks} = {humanize.naturalsize(blksize*nblks)}')
    else:
        logger.warning('  Did not get valid response for SCSI block size limits.')

    last_exc = None
    flashid = None
    for name, model in models.items():
        if args.model == name or args.model is None:
            try:
                logger.info(f'Probing for {name} ...')
                flashid = model.probe(fd)
            except NotImplementedError as exc:
                last_exc = exc
            else:
                break
    else:
        if args.model:
            raise SystemExit(f"No match found: {last_exc.args[0]}") from last_exc
        else:
            raise SystemExit(f"No match found.")


    if flashid and args.lookup:
        try:
            summary = fdnext.fdnext_decode(flashid)
        except RuntimeError as exc:
            p.error("Error from NAND flash lookup server: {exc}")
        except Exception as exc:
            p.error(f"Unexpected error: {exc}")
        else:
            print(f'NAND flash chip summary for {flashid.hex()}: {" | ".join(summary)}')
            print(f'More info: {fdnext.FDNEXT_WEB_URL}/{flashid.hex()}')


if __name__ == '__main__':
    main()
