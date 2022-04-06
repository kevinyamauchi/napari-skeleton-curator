from napari_plugin_engine import napari_hook_implementation

from .qt_skeleton_curator import QtSkeletonCurator
from .qt_skeleton_pruner import QtSkeletonPruner


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [QtSkeletonCurator, QtSkeletonPruner]