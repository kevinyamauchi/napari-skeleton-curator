import napari
from skimage import io


image = io.imread('./control-1.lsm-C3-MAX.tiff')
viewer = napari.view_image(image, name='raw')
viewer.tooltip.visible = True

napari.run()