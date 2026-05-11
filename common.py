from typing import Optional

def bytesy(*args: list[bytes | str | int], zpad: Optional[int] = None):
    b = bytearray()
    for arg in args:
        if isinstance(arg, bytes): b.extend(arg)
        elif isinstance(arg, str): b.extend(s.encode('ascii') if len(arg) == 1 else bytes.fromhex(arg))
        elif isinstance(arg, int): b.append(arg)
        else: raise NotImplementedError
    
    return bytes(b if zpad is None else b.ljust(zpad, b'\0'))

    