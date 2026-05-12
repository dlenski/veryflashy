import logging
from typing import Optional
from functools import wraps
from hexdump import hexdump

import py_sg

def bytesy(*args: list[bytes | str | int], zpad: Optional[int] = 0):
    '''Shorthand for creating bytes from literals. Accepts one or more arguments
    that are either:
      - bytes, bytearray: appended
      - str:
        - single ASCII character: decoded, appended
        - otherwise, hex-decoded and appended
      - int: appended as single byte

    Also accepts a `zpad` argument to zero-pad to the intended number of
    characters.
    '''
    b = bytearray()
    for arg in args:
        if isinstance(arg, (bytes, bytearray)): b.extend(arg)
        elif isinstance(arg, str): b.extend(s.encode('ascii') if len(arg) == 1 else bytes.fromhex(arg))
        elif isinstance(arg, int): b.append(arg)
        else: raise NotImplementedError

    return bytes(b.ljust(zpad, b'\0'))


logger = logging.getLogger()

@wraps(py_sg.read)
def sgread(fd, cmd, bufLen, timeout_ms=20_000, flags=0):
    logger.debug(f"SCSI read: {cmd.hex(sep=' ')}")
    try:
        res = py_sg.read(fd, cmd, bufLen, timeout_ms, flags)
    except py_sg.SCSIError as exc:
        ms, hs, ds, sense, buf = exc.args
        logger.debug(f"  Got error: [masked,host,driver]_status={ms:02x},{hs:02x},{ds:02x}")
        if sense:
            logger.debug(f"             sense={sense.hex(sep=' ')}")
        if buf:
            logger.debug(f"             buf={buf.hex(sep=' ')}")
        raise
    else:
        logger.debug(f"  Results:")
        for l in hexdump(res, 'generator'):
            logger.debug(l)
        return res
