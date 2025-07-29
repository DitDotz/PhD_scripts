
from __future__ import annotations
import traceback
import time
import math
import numpy as np
import matplotlib.pyplot as plt

from autoscript_tem_microscope_client import TemMicroscopeClient
from autoscript_tem_microscope_client.enumerations import OpticalMode, ProjectorMode
from autoscript_tem_microscope_client.structures import (
    AdornedImage,
    StagePosition,
)

from autoscript_tem_microscope_client.structures import StagePosition, StageVelocity

from autoscript_core.common import ApplicationServerException

import merlin_interface as mi

assert __name__ == "__main__"  # Don't import me!


START_ANGLE= StagePosition(a=math.radians(-10)) # to change before acq -50
STOP_ANGLE = StagePosition(a=math.radians(10)) # to change before acq 50

SAFE_ANGLE = math.radians(20) # specific for tomo 60

ZERO_TILT = StagePosition(a=math.radians(0))

TILT_SPEED = 1.5 # deg/s

tilt_position_list = []

if START_ANGLE.a>0:
    direction_vector = -1

else:

    direction_vector = 1

acq_tilt_velocities = StageVelocity(a=math.radians(TILT_SPEED * direction_vector)) # Important to check the direction! Otherwise you might exceed without knowing

def merlin_setup():
    merlin.threshold0 = 40
    # merlin.runheadless = 1 # for faster write speeds

    merlin.filedirectory=r'\\TALOS2SUPPORTPC\\Talos 2 Users\\Kho\\'
    merlin.fileenable = 1
    merlin.savealltofile = 1
    merlin.filename = 'default'

    merlin.counterdepth = 12
    merlin.acquisitiontime = 200 # ms default 200
    merlin.triggerstart = 0 # internal trigger
    merlin.triggerstop = 0 # internal trigger
    merlin.numframestoacquire = 0 # 0 for continuous until stopacquisition
    merlin.continuousrw = 1 # no gap time

    merlin.triggeroutttl = 0
    merlin.triggeroutlvds = 0

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

    print(f'new calibrated intensity : {microscope.optics.intensity}') # manually calibrate as necessary
    microscope.optics.intensity = 0.601 # parallel beam

    while microscope.specimen.stage.is_moving:
        print('stage not ready')

    print('wait for system to stabilize')
    time.sleep(2) 

except ApplicationServerException as err:
    print("Could not open column valves, quitting!")
    print(err)
    exit(0)

assert microscope.optics.optical_mode == OpticalMode.TEM # Change to TEM if required

try:

    microscope.specimen.stage.absolute_move(START_ANGLE)
    print('wait for holder to move to position')

    while microscope.specimen.stage.is_moving:
        print('stage not ready')

    time.sleep(2)

    print('holder is stable')

    microscope.detectors.screen.retract()
    
    # enter diffraction mode
    microscope.optics.projector_mode = ProjectorMode.DIFFRACTION

    # apertures = microscope.optics.aperture_mechanisms.C2.apertures
    # microscope.optics.aperture_mechanisms.C2.aperture = apertures[5]

    check = input('start acquisition?')

    microscope.optics.unblank()

    print('start tilting')
    microscope.specimen.stage.start_jogging(acq_tilt_velocities)

    print('starting merlin acq')
    print(f'tilt at {round(math.degrees(microscope.specimen.stage.position.a),2)}')
    tilt_position_list.append(round(math.degrees(microscope.specimen.stage.position.a),2))
    merlin.startacquisition()
    merlin.softtrigger()

    while True:
         
        if abs(microscope.specimen.stage.position.a) > abs(STOP_ANGLE.a):
            merlin.stopacquisition()
            tilt_position_list.append(round(math.degrees(microscope.specimen.stage.position.a),2))
            microscope.specimen.stage.stop_jogging()
            print('stopping merlin acq')
            print(f'{tilt_position_list}')
            break

        if abs(microscope.specimen.stage.position.a) >= SAFE_ANGLE:
            microscope.vacuum.column_valves.close()  
            microscope.specimen.stage.stop_jogging()
            microscope.specimen.stage.absolute_move(ZERO_TILT) 
            merlin.stopacquisition()
            print('exceeding safe angle limits')
            break

except Exception as err:
    microscope.vacuum.column_valves.close()  
    microscope.specimen.stage.stop_jogging()
    microscope.specimen.stage.absolute_move(ZERO_TILT) 
    merlin.stopacquisition()
    print("Encountered exception, closing column valves")
    traceback.print_exc()

finally:
    microscope.specimen.stage.stop_jogging() 
    merlin.stopacquisition()
    microscope.detectors.screen.insert()
    microscope.vacuum.column_valves.close()
    merlin.fileenable = 0 # set to no file saving

    # return to finding new areas of interest
    microscope.optics.projector_mode = ProjectorMode.IMAGING

    # plt.figure()
    # plt.plot(tilt_speed_list, 'x')
    # plt.show()