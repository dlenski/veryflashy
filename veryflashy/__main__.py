#!/usr/bin/env python

import argparse
import csv
import os
import logging
from pathlib import Path

import humanize

from .common import sgread, bytesy
from . import (
    phison,
    appotech,
    alcor,
    pl2530,
)
models = {n.__name__.split('.')[-1]: n for n in (phison, appotech, alcor, pl2530)}

logger = logging.getLogger(__name__)

def main():
    p = argparse.ArgumentParser(description='Identifies and inspects USB NAND flash drive controllers.')
    p.add_argument('-d', '--debug', default=0, action='count')
    p.add_argument('-m', '--model', choices=models.keys(), help=f'Flash controller type, if already known (one of {", ".join(models)})')
    p.add_argument('dev', help="Path to USB flash drive (e.g. /dev/sda or /dev/sg0)")
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
    assert res[3] >= 8 and len(res) >= 12
    nblks = int.from_bytes(res[4:8], 'big')
    blksize = int.from_bytes(res[10:12], 'big')
    print(f'  SCSI block size {blksize} x {nblks} = {humanize.naturalsize(blksize*nblks)}')

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


    if flashid:
        print("Done.")


if __name__ == '__main__':
    main()
