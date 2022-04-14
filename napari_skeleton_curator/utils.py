from typing import Tuple, Union

from napari.types import ImageData, LabelsData
import numpy as np
import pandas as pd
import skan
from skimage.exposure import exposure
from skimage.filters import gaussian,threshold_mean,frangi
from skimage.morphology import binary_dilation, disk, remove_small_holes, skeletonize


def preprocess_image(
        image: ImageData,   #! does not upload image
        gamma: float=1,     #! allow real time visulaisation
        gain: float=1,
        sigma: float=1,
        sigmas: float=1,
        area_threshold: float = 150
)-> ImageData:
    """ Image processing
    :param gamma(float) : Performs Gamma Correction on the input image.
    :param gain(float) : Performs Gamma Correction on the input image.
    :param sigma(float) : Gaussain filter
    :param sigmas(float) : Filter an image with the Frangi vesselness filter.
    :param area_threshold(float) : Sets size of holes when calling remove_small_holes

    :return:
     binary image with 1 pixel wide skeleton representation of image features
    """
    gamma_corrected = exposure.adjust_gamma(image, gamma=gamma, gain=gain)

    gaussian_original_image = gaussian(gamma_corrected, sigma=sigma)
    mean_thresh_gaussian = threshold_mean(gaussian_original_image)
    mean_binary = gaussian_original_image > mean_thresh_gaussian
    frangi_mean = frangi(mean_binary,sigmas=sigmas)

    remove_holes_binary = remove_small_holes(mean_binary, area_threshold=area_threshold)
    skeleton_mean_binary = skeletonize(remove_holes_binary)

    return skeleton_mean_binary


def make_skeleton(skeleton_im: ImageData) -> Tuple[LabelsData, pd.DataFrame, skan.Skeleton]:
    """
    Takes a binary (bool) skeleton and converts it into a Skan skeleton object

    :param skeleton_im (ImageData,bool): binary skeleton obtained from pre_process_image

    :return:
    csr_graph of  skeleton object
    table in the form of a pandas DataFrame,
    a labelled skeleton object


    """
    if skeleton_im.dtype != bool:
        raise TypeError('skeleton image should be a boolean image')
    skeleton_obj = skan.Skeleton(skeleton_im)
    summary = skan.summarize(skeleton_obj, find_main_branch=True)

    summary['index'] = np.arange(summary.shape[0]) + 1
    skel_labels = np.asarray(skeleton_obj)

    return skel_labels, summary, skeleton_obj


def remove_small_branches(
        skeleton: skan.Skeleton,
        summary: pd.DataFrame,
        min_branch_dist: float = 50,
        branch_type_0: bool = True,
        branch_type_1: bool = True,
        branch_type_2: bool = False,
        branch_type_3: bool = False,
):
    """

    :param skeleton: skan skeleton object from make_skeleton
    :param summary (pd.Dataframe) : skan skeleton summary from make_skeleton
    :param min_branch_dist (float): specifies minimum branch distance/length to be removed
    :param branch_type_0 :endpoint-to-endpoint (isolated branch
    :param branch_type_1:endpoint-to-endpoint (isolated branch
    :param branch_type_2:junction-to-junction
    :param branch_type_3:isolated cycle

    :return:
    pruned skeleton
    """

    too_short = (summary['branch-distance'] < min_branch_dist)

    types_to_prune = []
    if branch_type_0:
        types_to_prune.append(0)
    if branch_type_1:
        types_to_prune.append(1)
    if branch_type_2:
        types_to_prune.append(2)
    if branch_type_3:
        types_to_prune.append(3)
    wrong_type = summary['branch-type'].isin(types_to_prune)

    # Pruning is implemented in https://github.com/jni/skan/pull/117
    # pass in a list of branch ids to get a new skeleton with those branches
    # removed.
    to_cut = too_short & wrong_type
    pruned = skeleton.prune_paths(np.flatnonzero(to_cut))

    summary_pruned = skan.summarize(pruned)
    summary_pruned['index'] = np.arange(summary_pruned.shape[0]) + 1

    return pruned, summary_pruned


def fill_skeleton_holes(
        skeleton_im: LabelsData,
        dilation_size: int = 3
) -> Tuple[LabelsData, pd.DataFrame, skan.Skeleton]:
    """

    :param skeleton_im (ImageData,bool): binary skeleton obtained from pre_process_image
    :param dilation_size(int): size of selem
    :return:  fast binary morphological dilation of an image.
    """
    binary_skeleton = skeleton_im.astype(bool)
    dilated_skeleton = binary_dilation(binary_skeleton, selem=disk(dilation_size))

    filled_skeleton = skeletonize(dilated_skeleton)

    filled_obj = skan.Skeleton(filled_skeleton)
    filled_skeleton_labels = np.asarray(filled_obj)
    filled_skeleton_summary = skan.summarize(filled_obj)

    return filled_skeleton_labels, filled_skeleton_summary, filled_obj
