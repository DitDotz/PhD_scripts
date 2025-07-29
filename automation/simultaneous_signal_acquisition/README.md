# 4D-STEM HAADF

Assumes well-aligned STEM probe

4D-STEM performed using line trigger from HAADF acquisition

Missing functionality: 

SI trigger


## Merlin relevant notes


### Pixel trigger
If triggering is carried out using a pixel scanning clock, the triggers will need to be set to
start/stop on the external trigger. The frame time parameter will change its function - it will be
a time for which any additional trigger signals will be ignored. This is to avoid any problems if
the trigger signal contains ringing. For example, the microscope is set to acquire 1 ms dwell
time frames with a pixel clock; we can then safely select Frame Time = 0.5 ms which means
that any signals received 0.5 ms after the initial one will be ignored.
For some systems (e.g. EDS running from TIA in Thermo Fisher microscopes), the dwell
time on each pixel can vary due to additional detector synchronisation. In this case we
recommend using an internal stop trigger and exact frame time. This will also require a
number of frames per trigger set to 1.


#### Config for Merlin standard

 Triggering by pixel clock rising edge with 12-bit dynamic range. 1 ms time can be collected with the following settings:
SET,CONTINUOUSRW,1
SET,COUNTERDEPTH,12
SET,ACQUISITIONTIME,1
SET,ACQUISITIONPERIOD,1
SET,HVBIAS,120
SET,NUMFRAMESTOACQUIRE,100000
SET,NUMFRAMESPERTRIGGER,1
SET,THRESHOLD0,40
SET,THRESHOLD1,511
SET,TRIGGERSTART,1
SET,TRIGGERSTOP,0

CMD,STARTACQUISITION


### Line trigger
the Number of Frames/Trigger needs to match (or be smaller than) the number of scanning
positions per line to achieve a synchronised STEM scan. The frame time needs to be set
exactly the same as the frame time in the microscope setup. 

EDS spectrum imaging on Thermo Fisher microscopes, can include varying detector
synchronisation / refresh times during the scan. In this case, users may prefer acquiring with
a fixed Acquisition time instead, so each of the frames is collected with the same exposure
time

For Thermo FisherFEI microscopes, triggers are typically of LVDS type so TRIGGERSTART/TRIGGERSTOP should be 3/3 for pixel clock and 3/0 for line clock respectively.

3 - Rising Edge (LVDS)
0 - internal

#### Config for Merlin standard
Triggering by line clock rising edge with 6-bit dynamic range and 1 ms dwell time and
256x256 scan:

SET,CONTINUOUSRW,1
SET,COUNTERDEPTH,6
SET,ACQUISITIONTIME,1.0
SET,ACQUISITIONPERIOD,1.5
SET,HVBIAS,120
SET,NUMFRAMESTOACQUIRE,65536
SET,NUMFRAMESPERTRIGGER,256
SET,THRESHOLD0,40
SET,THRESHOLD1,511
SET,TRIGGERSTART,1
SET,TRIGGERSTOP,0
CMD,STARTACQUISITION
Note: Acquisition period may need to be longer than the length of the TTL signal. The
example above shows a triggering of a system where only a short tick is sent to Merlin at the
beginning of each line of the scan.