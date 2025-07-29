# Tilt series

## Description

Coordinate MERLIN camera acquisition with initiation of tilt series on TEM. End merlin acquisition when tilt series finishes.

## Problems encountered
resolved, error was due to not correctly setting file directory
There is no functionality in the API to actually set the velocity of the stage, only the piezostage even though there is a StageVelocity data structure.

partially resolved, workaround using jogging!
functionality was not in the docs but it is in the code package. start_jogging()
This is still not ideal, checked the speed and it is start-stop continuously, resulting in step-wise gradient instead of constant gradient
Still possible to use if you sync up the jogging with the frame time on merlin (i.e. if speed changes every 200ms then take one frame every 200ms)
