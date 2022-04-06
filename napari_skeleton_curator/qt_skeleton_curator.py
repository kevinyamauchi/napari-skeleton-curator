import magicgui
from napari.layers import Image
import numpy as np
from qtpy.QtWidgets import QWidget, QVBoxLayout, QPushButton

from .utils import preprocess_image, make_skeleton, remove_small_branches, fill_skeleton_holes


class QtSkeletonCurator(QWidget):

    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
        self.skeleton = {}
        self.summary = {}

        # turn on toolips
        self.viewer.tooltip.visible = True

        # make a widget for preprocessing


        self.pre_process_widget = magicgui.magicgui(
            preprocess_image,
            call_button='pre-process image',
            image={'choices': self._update_image_data}
        )
        self.viewer.layers.events.inserted.connect(
            self.pre_process_widget.reset_choices
        )
        self.viewer.layers.events.removed.connect(
            self.pre_process_widget.reset_choices
        )

        # make a button to skeletonize
        self.skeletonize_widget = magicgui.magicgui(
            make_skeleton,
            call_button='skeletonize image'
        )
        self.skeletonize_widget.called.connect(self._on_skeletonize)
        self.viewer.layers.events.inserted.connect(
            self.skeletonize_widget.reset_choices
        )
        self.viewer.layers.events.removed.connect(
            self.skeletonize_widget.reset_choices
        )

        # make a button to prune
        self.prune_widget = magicgui.magicgui(
            self._on_prune,
            call_button='Prune branches'
        )
        self.viewer.layers.events.inserted.connect(
            self.prune_widget.reset_choices
        )
        self.viewer.layers.events.removed.connect(
            self.prune_widget.reset_choices
        )

        # make a button to fill gaps in the skeleton
        self.fill_widget = magicgui.magicgui(
            fill_skeleton_holes,
            call_button='fill skeleton'
        )
        self.fill_widget.called.connect(self._on_fill)
        self.viewer.layers.events.inserted.connect(
            self.fill_widget.reset_choices
        )
        self.viewer.layers.events.removed.connect(
            self.fill_widget.reset_choices
        )

        # make a button to save
        self.save_btn = QPushButton("Save summary")
        self.save_btn.clicked.connect(self._on_save_summary)

        # todo: add layer selection
        self.selected_layer = 'segmentation'
        self.segments_to_prune = []

        # attach the mouse callback
        # labels_layer = self.viewer.layers[self.selected_layer]
        # labels_layer.mouse_drag_callbacks.append(self._on_mouse_click)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.pre_process_widget.native)
        self.layout().addWidget(self.skeletonize_widget.native)
        self.layout().addWidget(self.prune_widget.native)
        self.layout().addWidget(self.fill_widget.native)
        self.layout().addWidget(self.save_btn)

    def _update_image_data(self, event):
        # hacky way to get current image layers - ask Talley
        # how to improve...
        choices = []
        for layer in [x for x in self.viewer.layers if isinstance(x, Image)]:
            choice_key = f'{layer.name} (data)'
            choices.append((choice_key, layer.data))

        return choices

    def _on_pre_process(self):
        # get the image to pre-process
        im = self.viewer.layers['raw'].data

        # pass the image to our pre-process function
        preprocessed_im = preprocess_image(im, gamma=1.5, sigma=2, area_threshold=150)

        # add the preprocessed image as a new layer
        self.viewer.add_image(preprocessed_im, name='preprocessed')

    def _on_skeletonize(self, function_output):
        # get the results from the event object
        skeletononized_im, summary, skeleton_obj = function_output

        # store the skeleton data
        self.skeleton.update({'skeletonize': skeleton_obj})
        self.summary.update({'skeletonize': summary})

        # make the layer with the skeleton
        self.viewer.add_labels(skeletononized_im, name="skeletonize", properties=summary,)

    def _on_prune(
            self, min_branch_distance: float,
            branch_type_0: bool = True,
            branch_type_1: bool = True,
            branch_type_2: bool = False,
            branch_type_3: bool = False,):
        # prune the skeleton obj
        skeleton = self.skeleton['skeletonize']
        summary = self.summary['skeletonize']

        pruned, summary_pruned = remove_small_branches(
            skeleton,
            summary,
            min_branch_dist=min_branch_distance,
            branch_type_0=branch_type_0,
            branch_type_1=branch_type_1,
            branch_type_2=branch_type_2,
            branch_type_3=branch_type_3,
            )
        pruned_im = np.asarray(pruned)
        self.viewer.add_labels(pruned_im, properties = summary_pruned, name= 'prune')

    def _on_fill(self, function_output):
        # pass the image to our skeletonize function
        skeletononized_im, summary, skeleton_obj = function_output
        self.skeleton.update({'filled_skeleton': skeleton_obj})

        # Calculate the tortuosity of each branch
        # We define tortuosity as total branch length divided by Euclidean distance
        # between the endpoints (ranges [1, ∞))
        summary['tortuosity'] = (
                summary['branch-distance']
                / summary['euclidean-distance']
        )
        self.summary.update({'filled_skeleton': summary})

        self.viewer.add_labels(skeletononized_im, name="filled_skeleton", properties=summary)

    def _on_save_summary(self):
        summary_key= 'filled_skeleton'
        file_name = 'data.csv'
        summary = self.summary[summary_key]
        summary.to_csv(file_name)

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
