# From pairing session Juan <> Marlene 2021-05-06

import napari
import skan
from matplotlib import cm
from skimage import io
from skimage.exposure import exposure
from skimage.filters import gaussian
from skimage.filters import threshold_mean
from skimage.filters import frangi
from skimage.morphology import remove_small_holes
from skimage.morphology import skeletonize
from scipy.ndimage import distance_transform_edt
import numpy as np

image = io.imread('./control-1.lsm-C3-MAX.tiff')
viewer = napari.view_image(image)

# set the viewer to display the tooltip
# (e.g., shows properties on labels layer)
# this requires napari >= 0.4.9
# pip install --upgrade napari
viewer.tooltip.visible = True

gamma_corrected = exposure.adjust_gamma(image, 1.5)
viewer.add_image(gamma_corrected)
gaussian_original_image = gaussian(gamma_corrected, sigma=2)
mean_thresh_gaussian = threshold_mean(gaussian_original_image)
mean_binary = gaussian_original_image > mean_thresh_gaussian # create binary mask
viewer.add_labels(mean_binary)
frangi_mean = frangi(mean_binary, sigmas=2)
viewer.add_image(frangi_mean)
#skeleton_holy_binary = skeletonize(mean_binary)
#viewer.add_labels(skeleton_holy_binary)
remove_holes_binary = remove_small_holes(mean_binary, area_threshold=150)
skeleton_mean_binary = skeletonize(remove_holes_binary)
viewer.add_labels(remove_holes_binary)


# create a skeleton object with skan
skeleton = skan.Skeleton(skeleton_mean_binary)

# summarize branch properties -> pandas DataFrame
# Python Data Science Handbook by Jake VanderPlas
# tidy data by Hadley Wickham
# One row per branch
# One column per measurement
summary = skan.summarize(skeleton)
# see what properties skan computes per branch
#print(summary.describe())  # maybe. From memory
# branch indices start at 0
# but to display a label image in napari, we need labels starting at 1
# So np.asarray(Skeleton) returns an image with each branch index offset by 1
# and we modify the summary to contain this mapping (each label is mapped to
# itself + 1)
summary['index'] = np.arange(summary.shape[0]) + 1
skel_labels = np.asarray(skeleton)
# add the labels image with the summary as properties
# this allows us to see the properties in the status bar
# upcoming work:
#   - https://github.com/napari/napari/issues/2622
#   - https://github.com/napari/napari/issues/2596
viewer.add_labels(skel_labels, properties=summary)

# We want to prune branches less than 20 pixels long *and*
# that are not connecting branches, but rather terminal. See
# https://jni.github.io/skan/getting_started.html and search for
# "branch type" for branch type definitions
to_cut = (summary['branch-distance'] < 20) & (summary['branch-type'] < 2)

# Pruning is implemented in https://github.com/jni/skan/pull/117
# pass in a list of branch ids to get a new skeleton with those branches
# removed.
pruned = skeleton.prune_paths(np.flatnonzero(to_cut))

# some branches are merged in the new skeleton, so properties need to be
# recomputed.
#summary_pruned = skan.summarize(pruned)
#summary_pruned['index'] = np.arange(summary_pruned.shape[0]) + 1
#viewer.add_labels(np.asarray(pruned), name='pruned', properties=summary_pruned)

#########
# New chapter: hack to measure branch thickness
# skan measures pixel values along a skeleton if given those values (rather
# than a boolean-only skeleton). We can use the distance transform of the
# binary image to get at each pixel the distance from the background, which
# is the radius of the vessel.
distance = distance_transform_edt(remove_holes_binary)
viewer.add_image(distance)

# Make a skeleton with the distance transform as the value.
# For bonus points we add the pixel-pixel spacing in µm. Now distances will be
# in µm instead of pixels.
spacing = 581.82 / 1024
skeleton_float = skan.Skeleton(
        skeleton_mean_binary * distance * spacing,
        spacing=spacing,
        )

# now we repeat the same analysis as above
# For fun with units, check out the "pint" library
summary_float = skan.summarize(skeleton_float)
to_cut = (
        (summary_float['branch-distance'] < 50 * spacing)
        & (summary_float['branch-type'] < 2)
        )
pruned_float = skeleton_float.prune_paths(np.flatnonzero(to_cut))
summary_float_pruned = skan.summarize(pruned_float)
summary_float_pruned['index'] = np.arange(summary_float_pruned.shape[0]) + 1


# Calculate the tortuosity of each branch
# We define tortuosity as total branch length divided by Euclidean distance
# between the endpoints (ranges [1, ∞))
summary_float_pruned['tortuosity'] = (
        summary_float_pruned['branch-distance']
        / summary_float_pruned['euclidean-distance']
        )

# Change the next line if you want only a subset of columns
columns_we_want = summary_float_pruned.columns
summary_only_relevant = summary_float_pruned[columns_we_want]

labels_layer = viewer.add_labels(
        np.asarray(pruned_float),
        name='pruned float',
        properties=summary_float_pruned,
        )

# coloring labels images according to properties.
# this should become as easy as `labels_layer.color = 'property-name'`, but we
# are not there yet. So we need to pass in a dictionary mapping label values
# to color values.

# first, use matplotlib colormaps to map property values to a color.
# colormaps map floats in [0, 1] to their color range, OR
# uint8s in [0, 255].
# viridis is one of many colormaps provided by matplotlib. See:
# https://matplotlib.org/stable/tutorials/colors/colormaps.html
label_color = cm.viridis(
        summary_float_pruned['mean-pixel-value']
        / np.max(summary_float_pruned['mean-pixel-value'])
        )
# next, create the dictionary from the index to each color
color_dict = dict(zip(summary_float_pruned['index'], label_color))
labels_layer.color = color_dict

# You can save pandas dataframes, e.g.
summary_float_pruned.to_csv('data.csv')
napari.run()

