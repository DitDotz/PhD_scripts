import traceback
from pathlib import Path
from typing import List, Tuple
import time

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate2d
from skimage import filters, exposure, feature


from autoscript_tem_microscope_client import TemMicroscopeClient
from autoscript_tem_microscope_client.enumerations import DetectorType, OpticalMode
from autoscript_tem_microscope_client.structures import (
    Point,
    AdornedImage,
    StagePosition,
)

from autoscript_core.common import ApplicationServerException


assert __name__ == "__main__"  # Don't import me!


def bin_image(image: np.ndarray, bin_factor=4) -> np.ndarray:
    """
    Bins image of 1024 into 256, 256
    TODO: Make function more generic accepting any IMAGE_SIZE and BIN_FACTOR
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

def compute_translation_vector(current_im:np.ndarray, template:np.ndarray) -> np.ndarray:

    # If image2 is the reference and image1 is the shifted image:
    # The result of correlate2d(image2, image1) will have the peak correlation value indicating the best alignment of image1 with image2.
    # The peak position will still give you the shift, but in this case, it shows how image1 should be shifted to align with image2.
    # I.e. image2 is the reference

    # the resulting correlation matrix will have a size of (image2_height + image1_height - 1, image2_width + image1_width - 1).
    correlation = correlate2d(current_im, template, mode='full')
    
    # peak_index is relative to the correlation matrix
    # np.unravel_index() converts this index into a coordinate tuple (row, column)
    # outputs y,x
    peak_index = np.unravel_index(np.argmax(correlation), correlation.shape)

    # This center represents the point where the zero-shift alignment would be if template were perfectly aligned with current_im.
    # In other words, if you imagine placing template exactly in the middle of current_im without any shift, the peak of the correlation would be expected to be around this central position.
    # outputs y,x
    center = np.array(correlation.shape) // 2
    
    translation_vector = np.array(peak_index) - center
    # The translation vector calculated from cross-correlation tells you how much template needs to be shifted to best align with image2.
    # translation vector is relative to the center of the correlation image 
    # y, x
    
    # Flip to (x, y) format
    translation_vector = translation_vector[::-1]

    return translation_vector

def calculate_signed_angle_between_vectors(vec1:np.ndarray, vec2:np.ndarray)-> float:
    """
    Calculate the signed angle between two vectors.

    anti-clockwise from positive X-axis is positive angle

    Parameters:
    vec1 (numpy.ndarray): The desired vector.
    vec2 (numpy.ndarray): The observed vector.

    Returns:
    float: The signed angle between the two vectors in degrees.
    """
    # Compute the dot product
    dot_product = np.dot(vec1, vec2)
    
    # Compute the magnitudes of the vectors
    magnitude_vec1 = np.linalg.norm(vec1)
    magnitude_vec2 = np.linalg.norm(vec2)
    
    # Compute the cosine of the angle
    cos_theta = dot_product / (magnitude_vec1 * magnitude_vec2)
    
    # Clip the cosine value to avoid numerical issues with arccos
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    
    # Compute the angle in radians
    angle_radians = np.arccos(cos_theta)
    
    # Calculate the direction of the angle
    # Cross product to determine if it's positive or negative
    cross_product = np.cross(vec1, vec2)

    if cross_product < 0:
        angle_radians = -angle_radians
    
    # Convert the angle to degrees
    angle_degrees = np.degrees(angle_radians)
    
    return angle_degrees

def visualize_alignment(full_template_img:np.ndarray, current_im:np.ndarray, template:np.ndarray, translation_vector:np.ndarray)->None:

    '''
    Displays how the template is aligned with current_im
    Double check that the cross-correlate is working as intended, because it returns a result regardless of how good the fit is.
    '''

    x_shift, y_shift = translation_vector
    template_height, template_width = template.shape # y, x
    
    center_of_current_im_x = current_im.shape[1] / 2 # y, x
    center_of_current_im_y = current_im.shape[0] / 2

    center_of_template_x = x_shift + center_of_current_im_x 
    center_of_template_y = y_shift + center_of_current_im_y

    # rect is defined from the lower left corner
    rect_x_lower_left = center_of_template_x - template_width / 2 
    rect_y_lower_left = center_of_template_y - template_height / 2

    # Create a rectangle for the template
    template_rect = plt.Rectangle((rect_x_lower_left, rect_y_lower_left), template_width, template_height, 
                                  edgecolor='red', facecolor='none', linestyle='--')
    fig, ax = plt.subplots(1,3)

    ax[0].imshow(current_im, cmap='gray')
    ax[0].set_title('original im')
    ax[0].imshow(full_template_img)

    ax[1].set_title('translated im')
    ax[1].imshow(current_im)
    ax[1].add_patch(template_rect)
    ax[1].scatter(center_of_template_x, center_of_template_y, color='red', zorder=5, label='actual template center')
    ax[1].scatter(center_of_current_im_x, center_of_current_im_y, color='red', zorder=5, label='desired current_im center')
    
    ax[2].set_title('template')
    ax[2].imshow(template)

    # remove the x and y ticks
    for x in ax:
        x.set_xticks([])
        x.set_yticks([])
    
    plt.show()


def preprocess_image(image):
    # Apply Gaussian blur to reduce noise
    blurred_image = filters.gaussian(image, sigma=0.1) 
    # 0.1 value is specific to 79000x mag
    
    thresh = filters.threshold_yen(blurred_image)

    blurred_image = (blurred_image >= thresh).astype(int)

    # blurred_image = (feature.canny(blurred_image, sigma=3.0)).astype(int)
    return blurred_image

def image_to_beam_shift(px_col_vector_xy: np.ndarray, pixel_size: float, angle_deg: float = 22.4) -> Point:
    """
    Convert a vector from image space to beam shift space using a specified rotation angle.

    Parameters:
    px_vector_xy (np.ndarray): The input vector in image space.
    pixel_size (float): The size of a pixel in meters.
    angle_deg (float): The rotation angle in degrees (default is 22.4 degrees).

    Returns:
    Point: The transformed vector in beam shift space.
    """
    # Convert the angle from degrees to radians
    image_to_beam_shift_angle = np.radians(angle_deg)

    # Define the rotation matrix
    image_to_beam_shift_rotation_matrix = np.array([
        [np.cos(image_to_beam_shift_angle), -np.sin(image_to_beam_shift_angle)],
        [np.sin(image_to_beam_shift_angle),  np.cos(image_to_beam_shift_angle)]
    ], dtype=np.float64)
    
    # Scale the vector by pixel size
    vector_meters = px_col_vector_xy * pixel_size

    # Apply the rotation matrix to the coordinate system
    transformed_vector = image_to_beam_shift_rotation_matrix @ vector_meters

    # Microscope coordinate system is defined from bottom left, numpy is from upper left
    reflection_factor = -1
    desired_beam_shift = Point(x=transformed_vector[0][0], y=transformed_vector[1][0] * reflection_factor)

    return desired_beam_shift

def beam_to_image_shift(beam_shift_col_vector_xy: Point, pixel_size: float, angle_deg: float = 22.4) -> np.ndarray:
    """
    Convert a vector from beam shift space back to image space using a specified rotation angle.

    Parameters:
    beam_shift_vector (Point): The input vector in beam shift space.
    pixel_size (float): The size of a pixel in meters.
    angle_deg (float): The rotation angle in degrees (default is 22.4 degrees).

    Returns:
    np.ndarray: The transformed vector in image space.
    """
    # Convert the angle from degrees to radians
    image_to_beam_shift_angle = np.radians(angle_deg)

    # Define the rotation matrix
    image_to_beam_shift_rotation_matrix = np.array([
        [np.cos(image_to_beam_shift_angle), -np.sin(image_to_beam_shift_angle)],
        [np.sin(image_to_beam_shift_angle),  np.cos(image_to_beam_shift_angle)]
    ], dtype=np.float64)

    # Compute the inverse of the rotation matrix
    # Since rotation matrices are orthogonal, the inverse is the transpose
    rotation_matrix_inverse = image_to_beam_shift_rotation_matrix.T

    # Create the beam shift vector as a numpy array
    beam_shift_vector_np = np.array([beam_shift_col_vector_xy.x, beam_shift_col_vector_xy.y])

    # Reverse the reflection on the y-coordinate
    beam_shift_vector_refl = np.array([beam_shift_vector_np[0], beam_shift_vector_np[1] * -1])

    # Apply the inverse rotation matrix
    vector_meters = rotation_matrix_inverse @ beam_shift_vector_refl.T

    # Undo the scaling by dividing by pixel size
    vector_pixels = vector_meters / pixel_size

    return vector_pixels

# Initialize global variables
IMAGE_SIZE: int = 1024  # Assumes a square image i.e. IMAGE_SIZE_x = IMAGE_SIZE_y
DWELL_TIME:float = 500e-9 # s

# Higher means lesser chance of non-convergence on desired shift. Don't be afraid to use higher
# 0.6 was tested to be necessary to correct a 180 out-of-alignment (i.e. x is moving in the opposite direction of intended)
# This is the worst case scenario (exceeding 180 is just a <180 degree shift in the clockwise direction)

OVERLAP_FACTOR: float = 0.3
DESIRED_SHIFT_PX: int = int(IMAGE_SIZE * (1 - OVERLAP_FACTOR))  # in pixels

BIN_FACTOR:int = 4  # for processing cross-correlation to reduce computational time

# Start of script
print("Starting")
microscope = TemMicroscopeClient()
microscope.connect("192.168.0.1")

assert microscope.optics.optical_mode == OpticalMode.STEM 

FOV : float = microscope.optics.scan_field_of_view 
PIXEL_SIZE : float = FOV / IMAGE_SIZE # in metres

# Always work in PX in your script

try:
    microscope.vacuum.column_valves.open()
    time.sleep(3)  # Wait 5sec for vacuum to stabilise

except ApplicationServerException as err:
    print("Could not open column valves, quitting!")
    print(err)
    exit(0)

# save current stage position
original_stage_pos : StagePosition = microscope.specimen.stage.position
original_beam_shift: Point = Point(0,0)

# initialize with zero angle rotation if you wish to calibrate from start
image_to_beam_shift_angle: float = -44.7 # deg
# -44.7
adorned_image_list : list = []
images_list : list = []
correction_angle_list : list = [image_to_beam_shift_angle]

# initialize with zero angle rotation

guard_counter: int = 0

try:
    
    while True:

        # break if 6 or more attempts are made
        if guard_counter >= 5:
            break        

        guard_counter += 1

        # go back to original position for both stage and beam shift
        microscope.specimen.stage.absolute_move(original_stage_pos)
        microscope.optics.deflectors.beam_shift = original_beam_shift
        
        # wait for stage to finish moving
        while microscope.specimen.stage.is_moving==True:
            continue

        print('debug: stage has finished moving')
        
        # Take image
        adorned_image : AdornedImage = microscope.acquisition.acquire_stem_image(DetectorType.HAADF, 1024, DWELL_TIME)

        # Store copy of haadf data as numpy array
        image_data = np.copy(adorned_image.data).astype(np.float64)

        print('debug: acquired first haadf')

        # append original image to image lists
        adorned_image_list.append(adorned_image)
        images_list.append(image_data)

        # vector is in x, y
        # work in x-translation only 
        translation_vector_xy = np.array([[DESIRED_SHIFT_PX, 0]]).T  # Only x-direction shift
        
        desired_beam_shift = image_to_beam_shift(translation_vector_xy, PIXEL_SIZE, image_to_beam_shift_angle)
        
        microscope.optics.deflectors.beam_shift = desired_beam_shift

        print('debug: beam shifted')

        # Take image
        adorned_image = microscope.acquisition.acquire_stem_image(
            DetectorType.HAADF, IMAGE_SIZE, DWELL_TIME)

        # Store copy of haadf data as numpy array
        image_data = np.copy(adorned_image.data).astype(np.float64)
        
        print('debug: acquired second haadf')

        # append translated image to image lists
        adorned_image_list.append(adorned_image)
        images_list.append(image_data)

        # beam blank after acquiring both images
        microscope.optics.blank()

        # generate template from previous image
        full_template_img = images_list[-2]
        current_img = images_list[-1]

        # bin for faster processing
        # y, x format
        full_template_img = bin_image(full_template_img, BIN_FACTOR)
        current_img = bin_image(current_img, BIN_FACTOR)

        full_template_img = preprocess_image(full_template_img)
        current_img = preprocess_image(current_img)


        fig, axes = plt.subplots(2, 2)
        axes[0, 0].imshow(full_template_img)
        axes[0, 1].imshow(current_img)
        axes[1, 0].imshow(images_list[-2])
        axes[1, 1].imshow(images_list[-1])
        plt.show()

        # template is the desired overlapping part of the previous image to the right
        # y,x format
        template = generate_template(full_template_img, OVERLAP_FACTOR)

        # translation vector is relative to the centre of the desired center of current_image, whose absolute coordinates are set at (128,128)
        # definition is due to how the translation vector is defined wrt center of im2

        print('debug: performing cross-correlation')
        vector_from_desired_im2_center_to_template_match_index  = compute_translation_vector(current_img, template) # inputs are in y, x
        
        visualize_alignment(full_template_img, current_img, template, vector_from_desired_im2_center_to_template_match_index)

        # operating in x, y 
        # everything is relative to im2 desired binned coordinates (128, 128)
        center_im_2_desired_coord = np.array([IMAGE_SIZE/BIN_FACTOR/2, IMAGE_SIZE/BIN_FACTOR/2]) # fixed for specific binning

        center_im_1_starting_coord = center_im_2_desired_coord - np.array([DESIRED_SHIFT_PX/BIN_FACTOR, 0]) # fixed relative to desired motion hence overlap factor

        template_match_coord = center_im_2_desired_coord + vector_from_desired_im2_center_to_template_match_index
        center_im_2_actual_coord = template_match_coord + np.array([int(IMAGE_SIZE * (1 - OVERLAP_FACTOR))/BIN_FACTOR/2, 0]) # fixed relative to template match

        # vectors are end - start
        vector_from_center_im1_starting_coord_to_center_im_2_desired_coord = center_im_2_desired_coord - center_im_1_starting_coord

        vector_from_center_im1_starting_coord_to_im_2_actual_coord = center_im_2_actual_coord - center_im_1_starting_coord

        actual_desired_vector_magnitude_ratio = np.linalg.norm(vector_from_center_im1_starting_coord_to_im_2_actual_coord)/ np.linalg.norm(vector_from_center_im1_starting_coord_to_center_im_2_desired_coord)

        # angle might be flipped, have to check
        correction_angle = calculate_signed_angle_between_vectors(vector_from_center_im1_starting_coord_to_center_im_2_desired_coord, vector_from_center_im1_starting_coord_to_im_2_actual_coord) 

        # accounts for an edge case whereby the cross correlation fails when x is moving in the opposite direction
        # if the vector_from_desired_im2_center_to_template_match_index has positive x, it indicates it is on the right side of current_im instead of left

        if abs(correction_angle)<0.5:
            print(f'optimal angle correction: {sum(correction_angle_list)}')
            break
        
        print(f'correction_angle {correction_angle}')
        print(f'actual_desired_vector_magnitude_ratio: {actual_desired_vector_magnitude_ratio}') # ideal should be 1
        
        # keep track of correction_angles applied
        correction_angle_list.append(correction_angle)

        # iterate towards optimal angle
        image_to_beam_shift_angle +=correction_angle


except Exception as err:
    microscope.vacuum.column_valves.close()  # close column valves
    print("Encountered exception, closing column valves")
    traceback.print_exc()  # Print error

finally:
    # microscope.vacuum.column_valves.close()
    microscope.optics.deflectors.beam_shift = Point(0,0)

    # verify that they match up.
    print(f'final angle: {image_to_beam_shift_angle}')



