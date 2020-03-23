
import matplotlib.patches as mpatches
from skimage.segmentation import find_boundaries
from skimage.draw import line_nd

from scipy.spatial.distance import cdist
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import PIL.Image
import time
import meshio
from scipy import ndimage
from skimage.measure import label, regionprops, marching_cubes_lewiner
from skimage.external import tifffile









def scatter_bw_img(bw_img, x_resolution, y_resolution, z_resolution, max_dots=7000):
    """
    Visualize a 3D image. Used for testing the data at various stages in the pipeline
    :param bw_img: np array - binary 3D image
    :param x_resolution:
    :param y_resolution:
    :param z_resolution:
    :param max_dots:
    :return:
    """

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    indices_pix = np.argwhere(bw_img)
    indices = indices_pix * np.array([x_resolution, y_resolution, z_resolution])
    n = indices.shape[0]
    delta = int(n / max_dots)

    # Hacky-axis-equal taken from https://stackoverflow.com/a/13701747/11756605
    max_range = np.array([indices[:, 0].max() - indices[:, 0].min(),
                          indices[:, 1].max() - indices[:, 1].min(),
                          indices[:, 2].max() - indices[:, 2].min()]).max()
    Xb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][0].flatten() + 0.5 * (indices[:, 0].max() + indices[:, 0].min())
    Yb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][1].flatten() + 0.5 * (indices[:, 1].max() + indices[:, 1].min())
    Zb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][2].flatten() + 0.5 * (indices[:, 2].max() + indices[:, 2].min())
    for xb, yb, zb in zip(Xb, Yb, Zb):
        ax.plot([xb], [yb], [zb], 'w')


    ax.scatter(indices[::delta, 0],
               indices[::delta, 1],
               indices[::delta, 2],
               s=2,
               c='r')
    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")
    ax.set_zlabel("Z (um)")
    plt.show()


def tif_reader(path, color_idx=0):
    """
    Read a 3D image stored as .tif files in a folder into a np array
    :param path:
    :param color_idx:
    :return: np array - 3D image
    :return: float - xy_resolution (um/pix)
    """

    fnames = glob.glob(path + '/*.tif')
    fnames.sort()
    num_images = len(fnames)
    sample_img = plt.imread(fnames[0])

    size_x = sample_img.shape[0]
    size_y = sample_img.shape[1]

    # Read resolution from .tif metadata
    with tifffile.TiffFile(fnames[0]) as tif:
        resolution_tuple = tif.pages[0].tags['x_resolution'].value

    all_array = np.zeros((size_x, size_y, num_images))

    for idx, fname in enumerate(fnames):
        img = plt.imread(fname)
        all_array[:, :, idx] = img[:, :, color_idx]

    return all_array, resolution_tuple[1]/resolution_tuple[0]


def get_cell_surface(path, output_path, z_resolution=0.8, ss=1):
    """
    Takes the raw experimental data (3D multichannel image) and generates a raw triangle mesh

    :param path:
    :param output_path:
    :param z_resolution:
    :param ss: int - step size for marching_cubes method
    :return:
    """

    intensity_threshold = 1
    area_threshold = 40

    # import the image file
    raw_img, xy_resolution = tif_reader(path)
    # apply Gaussian filter
    filtered_img = ndimage.gaussian_filter(raw_img, 1)
    # threshold the image
    bw_img = filtered_img > intensity_threshold

    # find connected volumes
    label_img = label(bw_img, connectivity=bw_img.ndim)
    print("Labeled")
    props = regionprops(label_img)
    print("Propped")
    assert len(props) > 0, "No connected volumes found."
    areas = []
    for idx, p in enumerate(props):
        print(str(idx) + "/" + str(len(props)))
        areas.append(p.area)
        if p.area < area_threshold:
            bw_img[label_img == (idx+1)] = 0
    scatter_bw_img(bw_img, xy_resolution, xy_resolution, z_resolution, max_dots=12000)
    arg = np.argmax(areas)

    ####################################################
def test():
    # bw_img = np.load("test_data/20deg_ellipses.npy")
    bw_img = np.load("Cell/CytoD0000.tif")
    bw_img_after_growth = growth_v1(bw_img)

    # compare the image before and after growth
    scatter_bw_img(bw_img)
    scatter_bw_img(bw_img_after_growth)
    scroll_view_compare(bw_img, bw_img_after_growth)

def growth_v1(bw_img):
    img_after_growth = np.copy(bw_img)
    # Label raw image
    label_img = label(bw_img, connectivity=bw_img.ndim)
    props = regionprops(label_img)
    assert len(props) > 0, "No connected volumes found."
    nrows = bw_img.shape[0]
    ncols = bw_img.shape[1]
    nz = bw_img.shape[2]
    QUERY = False
    if QUERY:
        print(props[0].label)
        print(props[0].bbox)
        print(props[0].image.shape)
        print(find_boundaries(props[0].image).shape)

    def find_region_boundaries(region):
        bbox = region.bbox
        boundary_coords = np.array(np.where(find_boundaries(region.image)))
        boundary_coords[0, :] += bbox[0]
        boundary_coords[1, :] += bbox[1]
        boundary_coords[2, :] += bbox[2]
        boundary_coords = np.transpose(boundary_coords)
        return boundary_coords

     def connect(region1, region2, img):
         X1 = find_region_boundaries(region1)
        X2 = find_region_boundaries(region2)
        Y = cdist(X1, X2)
        # for each boundary point of region2, find the nearest point on the boundary of
        # region 1, then connects the two points
        coords = np.where(Y == np.amin(Y, axis=0))
        for n1, n2 in list(zip(coords[0], coords[1])):
              p1 = X1[n1, :]
              p2 = X2[n2, :]
             lin = line_nd(p1, p2)
             img[lin] = 1

    connect(props[0], props[1], img_after_growth)
    connect(props[1], props[0], img_after_growth)
    img_after_growth = ndimage.morphology.binary_fill_holes(img_after_growth)
    # use bounding rectangles to mark different regions
    fig, ax = plt.subplots(1, 1)
    for region in props:
           # print(region.area)
         minr, minc, minh, maxr, maxc, maxh = region.bbox
         rect = mpatches.Rectangle((minc, minr), maxc - minc, maxr - minr,
                                      fill=False, edgecolor='red', linewidth=2)
         ax.add_patch(rect)
    plt.tight_layout()
    # view the original label maps
    scroll_view(label_img, fig, ax)
    plt.show()
    return img_after_growth

def growth_v0(bw_img):
     img_after_growth = np.copy(bw_img)
    # Label raw image
    label_img = label(bw_img, connectivity=bw_img.ndim)
    props = regionprops(label_img)
     assert len(props) > 0, "No connected volumes found."
    nrows = bw_img.shape[0]
    ncols = bw_img.shape[1]
    nz = bw_img.shape[2]
    D = np.sqrt(nz * nz + nrows * nrows + ncols * ncols)

      def score(region, shape):
         score_map = np.zeros(shape)
        centroid = region.centroid
        for index, x in np.ndenumerate(score_map):
             d = np.linalg.norm(np.array(index) - np.array(centroid))
            score_map[index] = np.exp(-d / D)
        return score_map

    score_map_a = score(props[0], bw_img.shape)
    score_map_b = score(props[1], bw_img.shape)
    score_map_sum = score_map_a + score_map_b
    for index, x in np.ndenumerate(score_map_sum):
         if x > 1.6:
              img_after_growth[index] = 1
        else:
             img_after_growth[index] = 0
    # use bounding rectangles to mark different regions
    fig, ax = plt.subplots(1, 1)
    for region in props:
         # print(region.area)
         minr, minc, minh, maxr, maxc, maxh = region.bbox
        rect = mpatches.Rectangle((minc, minr), maxc - minc, maxr - minr,
                                      fill=False, edgecolor='red', linewidth=2)
         ax.add_patch(rect)
     plt.tight_layout()
    # view the original label maps
    scroll_view(label_img, fig, ax)
    plt.show()
    return img_after_growth

    ####################################################

    # isolate the cell
    bw_img_cell = np.zeros(bw_img.shape)
    cell_indices = np.argwhere(label_img == (arg + 1))
    bw_img_cell[cell_indices[:, 0],
                cell_indices[:, 1],
                cell_indices[:, 2]] = 1

    # flip the ii and jj dimensions to be compatible with the marching cubes algorithm
    bw_img_cell = np.swapaxes(bw_img_cell, 0, 1)

    # get the cell surface mesh from the marching cubes algorithm and the isolated cell image
    # https://scikit-image.org/docs/dev/api/skimage.measure.html#skimage.measure.marching_cubes_lewiner
    verts, faces, normals, _ = marching_cubes_lewiner(bw_img_cell,
                                                      spacing=(xy_resolution,
                                                               xy_resolution,
                                                               z_resolution),
                                                      step_size=ss)

    # save surface mesh info
    meshio.write(output_path + "_ss" + str(ss) + ".stl",
                 meshio.Mesh(points=verts,
                             cells={"triangle": faces}))


if __name__ == "__main__":
    test()
    x_resolution = 141.7 / 512
    y_resolution = 141.7 / 512
    z_resolution = 120 / 176

    gel_int = str(1)
    gel_state = "CytoD"
    date = str(10092019)
    path_to_raw_images = "/Users/ilitzkyd/Downloads/Cell"  # Go all the way to '/Cell'
    output_path = "/Users/ilitzkyd/Desktop"

    get_cell_surface(path_to_raw_images,
                     output_path,
                     x_resolution,
                     y_resolution,
                     z_resolution,
                     ss=2)