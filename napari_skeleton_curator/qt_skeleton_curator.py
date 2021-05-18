from napari_plugin_engine import napari_hook_implementation
import numpy as np
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton

from .utils import preprocess_image, make_skeleton, remove_small_branches

class QtSkeletonCurator(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.skeleton = {}
        self.summary = {}

        # make a button to pre-process
        self.pre_process_btn = QPushButton("Pre-process image")
        self.pre_process_btn.clicked.connect(self._on_pre_process)

        # make a button to skeletonize
        self.skeletonize_btn = QPushButton("Skeletonize image")
        self.skeletonize_btn.clicked.connect(self._on_skeletonize)

        # make a button to prune
        self.prune_btn = QPushButton("Prune image")
        self.prune_btn.clicked.connect(self._on_prune)

        # todo: add layer selection
        self.selected_layer = 'segmentation'
        self.segments_to_prune = []

        # attach the mouse callback
        # labels_layer = self.viewer.layers[self.selected_layer]
        # labels_layer.mouse_drag_callbacks.append(self._on_mouse_click)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.pre_process_btn)
        self.layout().addWidget(self.skeletonize_btn)
        self.layout().addWidget(self.prune_btn)


    def _on_pre_process(self):
        # get the image to pre-process
        im = self.viewer.layers['raw'].data

        # pass the image to our pre-process function
        preprocessed_im = preprocess_image(im, gamma=1.5, sigma=2, area_threshold=150)

        # add the preprocessed image as a new layer
        self.viewer.add_image(preprocessed_im, name='preprocessed')

    def _on_skeletonize(self):

        # get the image to skeletonize
        im = self.viewer.layers['preprocessed'].data

        # pass the image to our skeletonize function
        skeletononized_im, summary, skeleton_obj = make_skeleton(im)
        self.skeleton.update({'skeletonize': skeleton_obj})
        self.summary.update({'skeletonize': summary})

        # make the layer with the skeleton
        self.viewer.add_labels(skeletononized_im, name="skeletonize", properties=summary,)



    def _on_prune(self):
        # prune the skeleton obj
        skeleton = self.skeleton['skeletonize']
        summary = self.summary['skeletonize']

        pruned, summary_pruned = remove_small_branches(
            skeleton,
            summary,
            min_branch_dist=20,
            max_branch_type=2
        )
        pruned_im = np.asarray(pruned)
        self.viewer.add_labels(pruned_im, properties = summary_pruned, name= 'prune')

    def _on_mouse_click(self, layer, event):
        if layer.name == self.selected_layer:
            selected_label = layer.get_value(event.position, world=True) or 0
            self._toggle_label(selected_label)
            print(self.segments_to_prune)

    def _toggle_label(self, label_value):
        if label_value != 0:
            if label_value in self.segments_to_prune:
                self.segments_to_prune.remove(label_value)
                self._update_segment_alpha(label_value, 1)
            else:
                self.segments_to_prune.append(label_value)
                self._update_segment_alpha(label_value, 0)

    def _update_segment_alpha(self, label_value, alpha:float):
        selected_layer = self.viewer.layers[self.selected_layer]
        color_map = selected_layer.color
        current_color = color_map[label_value]
        current_color[3] = alpha
        color_map.update({label_value: current_color})
        selected_layer.color = color_map

@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return QtSkeletonCurator

