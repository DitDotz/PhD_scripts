from __future__ import annotations
import traceback
import time

import matplotlib.pyplot as plt
import numpy as np

from autoscript_tem_microscope_client import TemMicroscopeClient
from autoscript_tem_microscope_client.enumerations import OpticalMode, DetectorType, ImageSize
from autoscript_tem_microscope_client.structures import (
    AdornedImage,
    StagePosition,
)

from autoscript_core.common import ApplicationServerException


import merlin_interface as mi


assert __name__ == "__main__"  # Don't import me!

DWELL_TIME =  0.001 # in seconds! so 1 ms currently

IMAGE_SIZE = 128

def merlin_setup():
    merlin.threshold0 = 40
    merlin.runheadless = 1 # makes it write faster but you don't get real-time view of DPs

    merlin.filedirectory=r'\\TALOS2SUPPORTPC\\Talos 2 Users\\Kho\\technique_development'
    merlin.fileenable = 1
    merlin.savealltofile = 1
    merlin.filename = 'default'

    merlin.counterdepth = 6 # bit
    merlin.continuousrw = 1
    merlin.acquisitiontime = DWELL_TIME * 1000 # already in ms so change to s
    merlin.triggerstart = 1 # rising edge LVDS did not work, trying TTL. TTL works.
    merlin.triggerstop = 0 # internal trigger
    merlin.numframespertrigger = IMAGE_SIZE
    merlin.numframestoacquire = IMAGE_SIZE*IMAGE_SIZE
    merlin.triggeroutttl = 0
    merlin.triggeroutlvds = 0

    # merlin.hvbias = 120 # no idea what this is for
    merlin.acquisitionperiod = 1.5 # seems to be only for ttl signal
    return


print("Starting")

microscope = TemMicroscopeClient()
microscope.connect("192.168.0.1")
print('microscope connected')

merlin = mi.MerlinInterface(tcp_ip="192.168.0.4", tcp_port=6341, test_mode=False)
merlin_setup()
print('merlin connected')

try:
    print("Opening column valves")
    microscope.vacuum.column_valves.open()
    print('wait for system to stabilize')
    time.sleep(3)  # Wait 3sec for vacuum to stabilise

except ApplicationServerException as err:
    print("Could not open column valves, quitting!")
    print(err)
    exit(0)

assert microscope.optics.optical_mode == OpticalMode.STEM # Change to TEM if required

try:
    merlin.startacquisition()
    print('merlin is armed')
    time.sleep(2)

    print('acquiring scan')
    image = microscope.acquisition.acquire_stem_image(DetectorType.HAADF, IMAGE_SIZE, DWELL_TIME)
    merlin.stopacquisition()

except Exception as err:
    microscope.vacuum.column_valves.close()  # close column valves
    print("Encountered exception, closing column valves")
    traceback.print_exc()  # Print error

finally:
    microscope.vacuum.column_valves.close()
    microscope.disconnect()
    plt.imshow(image.data, cmap="gray")
    plt.show()
    print('script ended')
