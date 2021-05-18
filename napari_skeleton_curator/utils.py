import numpy as np
import skan
from skimage.exposure import exposure
from skimage.filters import gaussian
from skimage.filters import threshold_mean
from skimage.morphology import remove_small_holes
from skimage.morphology import skeletonize


def preprocess_image(
        image: np.ndarray,
        gamma: float=1.5,
        sigma: float=2,
        area_threshold: float = 150
) -> np.ndarray:
    gamma_corrected = exposure.adjust_gamma(image, gamma)

    gaussian_original_image = gaussian(gamma_corrected, sigma=sigma)
    mean_thresh_gaussian = threshold_mean(gaussian_original_image)
    mean_binary = gaussian_original_image > mean_thresh_gaussian

    remove_holes_binary = remove_small_holes(mean_binary, area_threshold=area_threshold)
    skeleton_mean_binary = skeletonize(remove_holes_binary)

    return skeleton_mean_binary


def make_skeleton(skeleton_im: np.ndarray):
    skeleton_obj= skan.Skeleton(skeleton_im)
    summary = skan.summarize(skeleton_obj)

    summary['index'] = np.arange(summary.shape[0]) + 1
    skel_labels = np.asarray(skeleton_obj)

    return skel_labels, summary, skeleton_obj


def remove_small_branches(
        skeleton,
        summary,
        min_branch_dist: float = 20,
        max_branch_type: int = 2
):
    #    branch types can be selected as follows:
    #     0 = endpoint-to-endpoint (isolated branch)
    #     1 = junction-to-endpoint
    #     2 = junction-to-junction
    #     3 = isolated cycle
    to_cut = (summary['branch-distance'] < min_branch_dist) & (summary['branch-type'] < max_branch_type)

    # Pruning is implemented in https://github.com/jni/skan/pull/117
    # pass in a list of branch ids to get a new skeleton with those branches
    # removed.
    pruned = skeleton.prune_paths(np.flatnonzero(to_cut))

    summary_pruned = skan.summarize(pruned)
    summary_pruned['index'] = np.arange(summary_pruned.shape[0]) + 1

    return pruned, summary_pruned
