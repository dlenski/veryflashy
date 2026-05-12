**This doesn't work. On-drive CPU doesn't lose all power, I guess.**

In order to get new settings on the device to "take".

Turn off USB device power by port:
```
echo '1-3' | sudo tee /sys/bus/usb/drivers/usb/unbind (replace 1-3 with your device ID).
```

Turn back on:
```
echo '1-3' | sudo tee /sys/bus/usb/drivers/usb/bind.
```

Find what USB port each SCSI generic device is associated with:

```
$ ls -l /sys/bus/usb/devices/*/host*/target*/*:0:0:0/generic
lrwxrwxrwx 1 root root 0 May 10 00:31 /sys/bus/usb/devices/2-1:1.0/host3/target3:0:0/3:0:0:0/generic -> scsi_generic/sg2
lrwxrwxrwx 1 root root 0 May 10 00:31 /sys/bus/usb/devices/2-8:1.0/host2/target2:0:0/2:0:0:0/generic -> scsi_generic/sg1
```

Find what SCSI generic device a /dev/sdX is associated with:
```
$ ls -ld /sys/block/sd*/device/scsi_generic/sg*
drwxr-xr-x 3 root root 0 May 10 00:26 /sys/block/sda/device/scsi_generic/sg0
drwxr-xr-x 3 root root 0 May  9 21:49 /sys/block/sdb/device/scsi_generic/sg1
```