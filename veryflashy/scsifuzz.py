#!/usr/bin/env python

import argparse
import os
import sys
import logging
import time

from py_sg import read as sgread, write as sgwrite, SCSIError

logger = logging.getLogger(__name__)

p = argparse.ArgumentParser()
p.add_argument('-d', '--debug', action='store_true')
p.add_argument('dev', help="Path to USB flash drive (e.g. /dev/sda or /dev/sg0)")
p.add_argument('-s', '--skip', default=[], action='append', help="Skip this CDB prefix, hexadecimal (e.g. C0FF or C234)")
p.add_argument('-t', '--timeout', default=20_000, type=int, help="Timeout in milliseconds (default %(default)s)")
p.add_argument('-n', '--size', default=1024, type=int, help="Number of bytes to attempt to read (default %(default)s)")
args = p.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)


skip = set()
for s in args.skip:
    s = bytes.fromhex(s)
    if len(s) < 1 or len(s) > 2:
        p.error(f"Skip argument {s.hex()} must be one or two bytes")
    skip.add(s)

fd = os.open(args.dev, os.O_RDWR)

# List of all (?) SCSI opcodes: https://www.t10.org/lists/op-num.htm
# List of all (?) SCSI opcodes required by UMS devices: https://web.archive.org/web/20210302020418/http://aidanmocke.com/blog/2020/12/30/USB-MSD-1/

avoid = {
    **{opcode: 'UMS'    for opcode in (0x00, 0x03, 0x12, 0x1a, 0x1b, 0x1e, 0x23, 0x25, 0x28, 0x2a, 0x2f)},
    **{opcode: 'FORMAT' for opcode in (0x04,)},
    **{opcode: 'WRITE'  for opcode in (0x0a, 0x10, 0x2a, 0x2e, 0x3b, 0x3f, 0x41, 0x50, 0x51, 0x53)}
}

def opcode_g_len_res(opcode):
    if opcode <= 0x1f:   return (0, 6, None)   # group 0
    elif opcode <= 0x3f: return (1, 10, None)  # group 1
    elif opcode <= 0x5f: return (2, 10, None)  # group 2
    elif opcode <= 0x7f: return (3, 10, 'res') # group 3 (res)
    elif opcode <= 0x9f: return (4, 16, None)  # group 4
    elif opcode <= 0xbf: return (5, 12, None)  # group 5
    elif opcode <= 0xdf: return (6, 10, 'res') # group 6 (res)
    elif opcode <= 0xff: return (7, 10, 'res') # group 7 (res)



for b1 in range(256):
    for b0 in range(256):

        if reason := avoid.get(b0):
            logger.debug(f"Avoiding SCSI opcode {b0:02x} because it's a {reason} opcode")
            continue
        elif bytes((b0,)) in skip:
            logger.debug(f"Avoiding --skip'ed SCSI opcode {b0:02x}")
            continue
        elif bytes((b0, b1)) in skip:
            logger.debug(f"Avoiding --skip'ed SCSI prefix {b0:02x} {b1:02x}")
            continue

        g, l, r = opcode_g_len_res(b0)
        cmd = bytes([b0, b1] + [0]*(l-2))
        try:
            res = sgread(fd, cmd, args.size, timeout_ms=args.timeout)
            logger.info(f"Trying SCSI read command with CDB {cmd.hex()}...")
            logger.info(f"  Got {len(res)} bytes: {res.hex()}")
        except OSError as exc:
            logger.error(f"Tried SCSI read command with CDB {cmd.hex()}, OS Error...")
            p.error(f"  Can't continue: {exc}")
        except SCSIError as exc:
            ms, hs, ds, sense, buf = exc.args
            
            for ii in range(20):
                try:
                    res = sgread(fd, b'\0\0\0\0\0\0', 0, timeout_ms=1000)   # test unit ready
                except SCSIError as exc:
                    time.sleep(1)
                except OSError as exc:
                    logger.error(f"Tried SCSI read command with CDB {cmd.hex()}, SCSI error...")
                    logger.error(f"  SCSI error: ms={ms}, hs={hs}, ds={ds}, sense={sense}, buf={buf}")
                    logger.error(f"  Test unit ready iter {ii}, OS Error...")
                    p.error(f"  Can't continue: {exc}")
                else:
                    logger.debug(f"Tried SCSI read command with CDB {cmd.hex()}, SCSI error...")
                    logger.debug(f"  SCSI error: ms={ms}, hs={hs}, ds={ds}, sense={sense}, buf={buf}")
                    if ii > 0:
                        logger.debug(f"   Test unit ready took {ii} 1-second delays to become okay again ({res.hex()}).")
                    break
	