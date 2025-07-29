# Calibrate coordinate systems

beam shift coordinate system

stage shift coordinate system

image coordinate system

Determine the rotation matrix angle necessary to translate a shift in image coordinate system to stage shift or beam shift in STEM mode. TEM mode requires a different calibration at different magnifications=

 ## What the script does

Takes a HAADF image at current stage position Applies a known pixel translation shift transformed into metres via (pixel_shift * pixel_size) Takes a HAADF image at new stage position Performs cross-correlation Determines angle necessary to translate the correct input stage/beam shift

Using the results
Apply the angle in the rotation matrix for each coordinate system to an applied pixel translation vector

stage shift = stage_rotation matrix * px translation vector * pixel_size_m beam shift = beam_rotation matrix * px translation vector * pixel_size_m

## Limitations of script
Does not work if the angle is wildly off resulting in no overlap between the first and second image

Try a higher overlap (might help with high angle corrections)

Max working angle to correct - 130 at 0.5 overlap

Don't need to check beyond 180, can always go negative angles (clockwise from positive x-axis)

Only the first correction has high accuracy for some reason

Binning affects the accuracy of subsequent corrections (the first correction is always the best)

## Stage shift to solve

It is consistently not moving the correct vector magnitude.

In fact, the displayed actual_desired_vector_magnitude_ratio is >1 when it should be < 1 from observations

Need to implement like a - continue moving some more until the ratio is close to 1 then check for the angle.

PIEZO and normal stage angle might be calibrated differently??

-23.47 for piezo

angle correction can only be done if the vector magnitude is correct

there is inconsistency between what is printed under piezo and what is obtained from image vectors
