"""tiling.py

Acquires HAADF in a tile-like fashion with specified number of rows and columns of images.

Corrects for stage drift/incorrect stage movement

Assumes microscope is already aligned in STEM mode

Assumes a square 1024*1024 image being acquired

Assumes imageX/Y is the same as stage X/Y
"""

import traceback
from pathlib import Path
from typing import List, Tuple

import numpy as np
import PIL
import matplotlib.pyplot as plt
from scipy.signal import correlate2d


from autoscript_tem_microscope_client import TemMicroscopeClient
from autoscript_tem_microscope_client.enumerations import DetectorType, OpticalMode
from autoscript_tem_microscope_client.structures import (
    Point,
    AdornedImage,
    StagePosition,
)

assert __name__ == "__main__"  # Don't import me!


def connect_to_microscope(ip_address: str = "192.168.0.1") -> TemMicroscopeClient:
    print("Starting")
    microscope = TemMicroscopeClient()  # Start up client
    microscope.connect(ip_address)  # Connect to microscope server
    return microscope


def bin_image(image: np.ndarray, bin_factor=4) -> np.ndarray:
    """
    Bins image of 1024 into 256, 256
    TODO: Make function more generic accepting any IMAGE_SIZE and bin_factor
    """
    # this bin function is abit wonky because it assumes constant image size of 1024
    binned_img = image.reshape(256, bin_factor, 256, bin_factor)

    # Sum along the last two axes to bin the pixels
    binned_img = np.sum(binned_img, axis=(1, 3))

    # Normalize the values if needed
    binned_img = binned_img / (bin_factor * bin_factor)
    return binned_img


def generate_template(image: np.ndarray, overlap_factor: float) -> np.ndarray:
    """
    Reduce area to template match from previous image compared to current image.
    Template is always on the right side
    """
    template = image[:, int(image.shape[1] * (1 - overlap_factor)) :]
    return template


def cross_correlate(image: np.ndarray, template: np.ndarray) -> Tuple[int, int]:
    """
    Computes the cross-correlation between an image and a template.

    Parameters:
        image (np.ndarray): The input image.
        template (np.ndarray): The template to correlate with the image.

    Returns:
        Tuple[int, int]: The peak index where the highest correlation occurs.
    """
    corr_map = correlate2d(image, template, mode="valid")
    peak_index = np.unravel_index(np.argmax(corr_map), corr_map.shape)
    return peak_index


NO_COLS_TO_TILE: int = 2  # Number of columns to tile
NO_ROWS_TO_TILE: int = 1  # Number of rows to tile

OVERLAP_FACTOR: float = (
    0.3  # Higher means lesser chance of non-convergence on desired shift
)

IMAGE_SIZE: int = 1024  # Assumes a square image i.e. image_size_x = image_size_y

DESIRED_SHIFT_PIXELS = IMAGE_SIZE * (1 - OVERLAP_FACTOR)  # in pixels

SHIFT_TOLERANCE_PIXELS = 5  # For optimizing peak_index, in pixels

BIN_FACTOR = 4  # for processing cross-correlation to reduce computational time

microscope = connect_to_microscope("192.168.0.1")
microscope.vacuum.column_valves.open()
assert microscope.optics.optical_mode == OpticalMode.STEM
original_stage_pos = microscope.specimen.stage.position

adornedImage_list = []
images_list = []

FOV = microscope.optics.scan_field_of_view
PIXEL_SIZE = FOV / IMAGE_SIZE
DESIRED_RELATIVE_SHIFT = DESIRED_SHIFT_PIXELS * PIXEL_SIZE  # in metres

try:
    for i in range(NO_ROWS_TO_TILE):  # Iterate over rows

        for j in range(NO_COLS_TO_TILE):  # Iterate over columns

            if i == 0 and j == 0:

                desired_abs_stage_pos = original_stage_pos
                print(f'desired_abs_stage_pos = {desired_abs_stage_pos}')

            elif j == 0:
                # For the first column in subsequent rows, update row and set col back to the left pos

                desired_abs_stage_pos = adornedImage_list[
                    -1
                ].metadata.stage_settings.stage_position + StagePosition(
                    y=DESIRED_RELATIVE_SHIFT  # update y
                )
                desired_abs_stage_pos.x = original_stage_pos.x  # set x back to the left
                print(f'desired_abs_stage_pos 1 = {desired_abs_stage_pos}')

            else:
                # For subsequent columns in the same row, update column but retain row

                desired_abs_stage_pos = adornedImage_list[
                    -1
                ].metadata.stage_settings.stage_position + StagePosition(
                    x=DESIRED_RELATIVE_SHIFT
                )  # move x to the right
                print(f'desired_abs_stage_pos 2 = {desired_abs_stage_pos}')

            microscope.specimen.stage.absolute_move(desired_abs_stage_pos)

            haadf_read_only = microscope.acquisition.acquire_stem_image(
                DetectorType.HAADF, 1024, 50e-9
            )
            haadf_data = np.copy(haadf_read_only.data).astype(np.float64)

            microscope.optics.blank()

            adornedImage_list.append(haadf_read_only)
            images_list.append(haadf_data)

        if j > 0:  # only corrects horizontally not vertically

            correction_attempts = 0
            print(f"image {i}{j}")

            while True:

                # generate template from previous image
                full_template_img = images_list[-2]

                current_img = images_list[-1]

                full_template_img = bin_image(full_template_img)
                current_img = bin_image(current_img)

                template = generate_template(full_template_img, OVERLAP_FACTOR)

                peak_index = cross_correlate(current_img, template)

                # Current implementation only corrects shift in horizontal direction
                # need to check how to handle scenario where by (0,2) goes to (1,0) (can't check based on last position)

                if (
                    abs(peak_index[0]) <= SHIFT_TOLERANCE_PIXELS
                    and abs(peak_index[1]) <= SHIFT_TOLERANCE_PIXELS
                ):
                    print("no shift correction necessary \n")

                    break

                print("Correcting shift...")

                # Calculate shift
                relative_overshift_x = peak_index[1] * BIN_FACTOR * PIXEL_SIZE
                relative_overshift_y = peak_index[0] * BIN_FACTOR * PIXEL_SIZE

                print(
                    f"relative_overshift: ({relative_overshift_y}, {relative_overshift_x})"
                )

                current_image_stage_pos = adornedImage_list[
                    -1
                ].metadata.stage_settings.stage_position

                # check positive or negative x shifts required
                if current_image_stage_pos.x > desired_abs_stage_pos.x:
                    microscope.specimen.piezo_stage.relative_move(
                        StagePosition(x=-relative_overshift_x)
                    )
                    print("translating left")

                else:
                    microscope.specimen.piezo_stage.relative_move(
                        StagePosition(x=relative_overshift_x)                    )
                    print("translating right")

                # check positive or negative y shifts required
                if current_image_stage_pos.y > desired_abs_stage_pos.y:
                    microscope.specimen.piezo_stage.relative_move(
                        StagePosition(y=-relative_overshift_y)
                    )
                    print("translating up")

                else:
                    microscope.specimen.piezo_stage.relative_move(
                        StagePosition(y=relative_overshift_y)
                    )
                    print("translating down")

                # re-acquire image
                haadf_read_only = microscope.acquisition.acquire_stem_image(
                    DetectorType.HAADF, 1024, 50e-9
                )

                haadf_data = np.copy(haadf_read_only.data).astype(np.float64)

                microscope.optics.blank()

                # replace images in list
                images_list[-1] = haadf_data
                adornedImage_list[-1] = haadf_read_only

                correction_attempts += 1

                if correction_attempts == 10:
                    print("No solution found \n")
                    break

    microscope.vacuum.column_valves.close()

    # Display the images in a grid
    from matplotlib import pyplot as plt

    n = len(images_list)
    fig, axes = plt.subplots(NO_ROWS_TO_TILE, NO_COLS_TO_TILE)

    for row in range(NO_ROWS_TO_TILE):
        for column in range(NO_COLS_TO_TILE):
            plot = axes[row, column]
            plot.axis("off")
            i = column + row * NO_COLS_TO_TILE
            plot.imshow(images_list[i], cmap="gray")

    plt.show()
    plt.savefig()

except Exception as err:
    microscope.vacuum.column_valves.close()  # close column valves
    microscope.specimen.stage.absolute_move_safe(original_stage_pos)
    traceback.print_exc()  # Print error
