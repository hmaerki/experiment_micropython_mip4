import os
import rp2
import os
import gc
import machine
import micropython
import _thread


micropython.alloc_emergency_exception_buf(100)

import utils_wlan


wlan = utils_wlan.WLAN()
# Make sure, the connection before the reboot is dropped.
# wlan.power_off()
wlan.connect()
print("Ready")
