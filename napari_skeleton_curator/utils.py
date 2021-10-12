from typing import Tuple, Union

from napari.types import ImageData, LabelsData
import numpy as np
import pandas as pd
import skan
from skimage.exposure import exposure
from skimage.filters import gaussian,threshold_mean,frangi
from skimage.morphology import binary_dilation, disk, remove_small_holes, skeletonize


def preprocess_image(
        image: ImageData,
        gamma: float=1,
        gain: float=1,
        sigma: float=1,
        sigmas: float=1,
        area_threshold: float = 150
) -> ImageData:
    gamma_corrected = exposure.adjust_gamma(image, gamma)

    gaussian_original_image = gaussian(gamma_corrected, gaussiansigma=sigma, gain=gain)
    mean_thresh_gaussian = threshold_mean(gaussian_original_image)
    mean_binary = gaussian_original_image > mean_thresh_gaussian
    frangi_mean = frangi(mean_binary,sigmas=sigmas)

    remove_holes_binary = remove_small_holes(mean_binary, area_threshold=area_threshold)
    skeleton_mean_binary = skeletonize(remove_holes_binary)

    return skeleton_mean_binary


def make_skeleton(skeleton_im: ImageData) -> Tuple[LabelsData, pd.DataFrame, skan.Skeleton]:
    if skeleton_im.dtype != bool:
        raise TypeError('skeleton image should be a boolean image')
    skeleton_obj= skan.Skeleton(skeleton_im)
    summary = skan.summarize(skeleton_obj)

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
    too_short = (summary['branch-distance'] < min_branch_dist)

    # get the branches that are of the type to cut
    #    branch types can be selected as follows:
    #     0 = endpoint-to-endpoint (isolated branch)
    #     1 = junction-to-endpoint
    #     2 = junction-to-junction
    #     3 = isolated cycle
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
    binary_skeleton = skeleton_im.astype(bool)
    dilated_skeleton = binary_dilation(binary_skeleton, selem=disk(dilation_size))

    filled_skeleton = skeletonize(dilated_skeleton)

    filled_obj = skan.Skeleton(filled_skeleton)
    filled_skeleton_labels = np.asarray(filled_obj)
    filled_skeleton_summary = skan.summarize(filled_obj)

    return filled_skeleton_labels, filled_skeleton_summary, filled_obj
