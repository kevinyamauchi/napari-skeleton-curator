from typing import List

import napari.layers
import numpy as np
import magicgui
from magicgui.widgets import Table
from napari.utils.events.containers import EventedList
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget
import skan


class QtSkeletonPruner(QWidget):

    def __init__(self, napari_viewer):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.viewer = napari_viewer

        # create combobox to select layer
        self.select_layer_widget = magicgui.magicgui(
            self._set_layer,
            call_button='select layer',
        )
        self.viewer.layers.events.inserted.connect(
            self.select_layer_widget.reset_choices
        )
        self.viewer.layers.events.removed.connect(
            self.select_layer_widget.reset_choices
        )

        # make the table
        self._columns_to_display = [
            'skeleton-id',
            'branch-distance',
            'main',
            'branch-type'
        ]
        init_table = {p: [] for p in self._columns_to_display}
        self.table = Table(init_table)

        # make a button to prune
        self.prune_btn = QPushButton("prune selected branches")
        self.prune_btn.clicked.connect(self.prune_selected_branches)
        self._selected_layer = ''

        self._selected_branches = EventedList([])

        # connect selected branches events to the table
        self.selected_branches.events.inserted.connect(self._update_table_from_selected_branches)
        self.selected_branches.events.removed.connect(self._update_table_from_selected_branches)
        self.selected_branches.events.changed.connect(self._update_table_from_selected_branches)

        self.layout().addWidget(self.select_layer_widget.native)
        self.layout().addWidget(self.table.native)
        self.layout().addWidget(self.prune_btn)

    @property
    def selected_layer(self) -> str:
        return self._selected_layer

    @selected_layer.setter
    def selected_layer(self, selected_layer):
        if selected_layer == "":
            return
        self._connect_mouse_events(selected_layer)

        self._selected_layer = selected_layer

    def _set_layer(self, layer: napari.layers.Labels):
        self.selected_layer = layer.name

    @property
    def selected_braches(self) -> EventedList[int]:
        return self._selected_branches

    @selected_braches.setter
    def selected_branches(self, selected_branches: EventedList[int]):
        self._selected_branches = EventedList[selected_branches]

    def _connect_mouse_events(self, selected_layer):
        if selected_layer != self.selected_layer:
            layer = self.viewer.layers[selected_layer]
            layer.mouse_drag_callbacks.append(self._on_mouse_click)

    def _on_mouse_click(self, layer, event):
        selected_label = layer.get_value(
            position=event.position,
            view_direction=event.view_direction,
            dims_displayed=event.dims_displayed
        )
        if selected_label != 0:
            if selected_label not in self.selected_branches:
                self.selected_branches.append(selected_label)
            else:
                self.selected_branches.remove(selected_label)
            print(self.selected_branches)

    def _update_table_from_selected_branches(self, event):
        if len(self.selected_branches) > 0:
            # if there are selected branches, we undo the offset of one
            # added for the Labels layer indexing.
            selected_branch_indices = np.asarray(self.selected_branches) - 1
        else:
            selected_branch_indices = []
        layer_props = self.viewer.layers[self.selected_layer].properties
        selected_properties = {p: layer_props[p][selected_branch_indices] for p in self._columns_to_display}
        self.table.value = selected_properties

    def prune_selected_branches(self):
        selected_layer = self.viewer.layers[self.selected_layer]
        skel_obj = selected_layer.metadata['skan_obj']
        if len(self.selected_branches) > 0:
            # if there are selected branches, we undo the offset of one
            # added for the Labels layer indexing.
            selected_branch_indices = np.asarray(self.selected_branches) - 1

            pruned = skel_obj.prune_paths(selected_branch_indices)

            summary_pruned = skan.summarize(pruned)
            summary_pruned['index'] = np.arange(summary_pruned.shape[0]) + 1
            pruned_im = np.asarray(pruned)
            self.viewer.add_labels(
                pruned_im,
                properties=summary_pruned,
                name='prune',
                metadata={'skan_obj': pruned}
            )

