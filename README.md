# veryflashy

Extracts information about the controller chips and
and NAND flash chips used in
[USB flash drives](https://en.wikipedia.org/wiki/USB_flash_drive).

Currently, it can interface with several common brands of USB NAND flash controller chips,
and can extract the NAND flash chip IDs from most of them:

| Manufacturer | Controller chip(s) | Flash chip ID? | Other features |
|:--------|:-----------:|:-------------:|:------------:|
| Phison | PS23xx | ✓ | Controller chip ID, controller firmware version, [partitioning info](https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2) |
| Alcor | AU698x | ✓ | |
| AppoTech | DM82xx | ✓ | |
| iCreate | i80xx | ✓ | |
| ?[^1] | PL2530 | ◌ | |

[^1]: I truly don't what company makes this flash chip, but my crude [fuzzer](#fuzzer)
was able to extract some information from an old USB drive, including the string "PL2530" and
the size of the flash in 512-byte blocks.

## Running it

| ⚠️ Warning |
|:-----------|
| This tool *tries* to issue only read-only commands, but since nearly all of them are undocumented and nonstandard, there's always a chance that it will delete or corrupt data from your USB flash drive. Don't run it unless you're okay with losing all of the data on the device, or even [bricking](https://en.wikipedia.org/wiki/Brick_(electronics)) it permanently. |

Check out this repository, then `sudo uv run veryflashy /dev/sdX` in it
(or `uv run sudo --preserve-env=PATH python -m veryflashy /dev/sdX`).
Add the `-l` option to look up information about the identity of the
NAND flash chip at [FlashMaster online](https://fm.itxtech.org/en):

```
$ sudo veryflashy -l /dev/sdb
Reading standard SCSI disk capacity (SCSI command 25 ...):
  SCSI block size 512 x 15663104 = 8.0 GB
Reading standard SCSI block limits (SCSI command 23 ...):
  SCSI block size 512 x 15663104 = 8.0 GB
Reading vendor info (SCSI command 06 05 ...):
  Phison chip ID: PS2251-32 (raw value 2232)
  Phison firmware version/date: 1.5.16
  Phison f1f2: ff01 (NOT SURE WHAT THIS IS)
  Phison USB ID 13fe:1f23
Reading vendor info (SCSI command 06 05 49 4e 46 4f):
  Phison split mode 3, split at 0 blocks
  (See https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2 for what this means)
Reading flash ID (06 56), this can take a while:
  Flash ID 89-d7-d5-3e-78-00
NAND flash chip summary for 89d7d53e7800: Intel | 4GB MLC | 2 die | 1 planes
More info: https://fm.itxtech.org/en/ids/89d7d53e7800
```

## Credits and inspiration

- [Phison drive mode configuration](https://gist.github.com/warewolf/e19d6817f1d59939a32fbd9e1a30b9d2)
- [Alcor flash controller hacking](https://github.com/tizbac/alcorhack) ([blog](https://linuxehacking.ovh/2014/07/20/alcor-ufd-controller-hacking-update-2/))

## Fuzzer 💡

I wrote a fuzzer ([scsifuzz.py](veryflashy/scsifuzz.py)) which just tries all possible 2-bytes prefixes for
[SCSI commands](https://en.wikipedia.org/wiki/SCSI#SCSI_command_protocol), excluding those which
are [part of the usual USB Mass Storage command set](https://web.archive.org/web/20210302020418/http://aidanmocke.com/blog/2020/12/30/USB-MSD-1/) (and
thus unlikely to access any hidden features) and those which seem like they could be unusually destructive
([having "write" or "format" in the description](https://www.t10.org/lists/2op.htm), for instance).

It's very crude, but seemingly effective. I was able to immediately figure out the AppoTech DM8233
controller chip with it.

## Goal

The goal of this tool is to be like "ChipEasy" or "ChipGenius",
but not some horrific black-box Windows EXE distributed on sketchy
malware-ridden websites, and written in broken
English, Russian, and Chinese.
