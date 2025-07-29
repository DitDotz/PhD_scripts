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

BUFFER_ANGLE = 5 # degs
DESIRED_START_ANGLE = 10  # degs
START_ANGLE= StagePosition(a=math.radians(-(DESIRED_START_ANGLE+BUFFER_ANGLE))) # to change before acq, starts from negative angle by default
STOP_ANGLE = StagePosition(a=math.radians(10)) # to change before acq

SAFE_ANGLE = math.radians(60) # specific for tomo

ZERO_TILT = StagePosition(a=math.radians(0))

TILT_SPEED = math.radians(1.5) # deg/s

if START_ANGLE.a>0:
    direction_vector = -1

else:

    direction_vector = 1

acq_tilt_velocities = StageVelocity(a=TILT_SPEED * direction_vector) # Important to check the direction! Otherwise you might exceed without knowing

microscope = TemMicroscopeClient()
microscope.connect("192.168.0.1")
print('microscope connected')

try:

    microscope.specimen.stage.absolute_move(START_ANGLE)
    print('wait for holder to move to position')

    while microscope.specimen.stage.is_moving:
        continue

    microscope.specimen.stage.absolute_move(START_ANGLE)
    time.sleep(2)
    print('holder is stable')
    print('start tilting')

    microscope.specimen.stage.start_jogging(acq_tilt_velocities)
    while True:
        time.sleep(0.05)
        print(round(math.degrees(microscope.specimen.stage.position.a),2))


except Exception as err:
    microscope.vacuum.column_valves.close()  
    microscope.specimen.stage.stop_jogging()
    microscope.specimen.stage.absolute_move(ZERO_TILT) 
    print("Encountered exception, closing column valves")
    traceback.print_exc()

finally:
    microscope.specimen.stage.stop_jogging() 
