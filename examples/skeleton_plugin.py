import napari
from skimage import io


image = io.imread('/home/marlene/Documents/Github/napari-skeleton-curator/control 1.lsm-C3-MAX.tiff')
viewer = napari.view_image(image, name='raw')

napari.run()