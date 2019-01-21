import numpy as np
import cv2


def find_clusters(a, allowed_jump=0, min_size=1):
    """
    Find clusters, where the index has jumps/discontinuities, i.e. [1, 2, 3, 7, 8, 9] contains 2 clusters. Input can
    also be boolean array.

    :param a: Array for cluster search. Can be array of index or bool values.
    :type a: np.core.multiarray.ndarray
    :param allowed_jump: Discontinuities which should not be considered a cluster break
    :type allowed_jump: int
    :param min_size: Minimum cluster size to keep
    :type min_size: int
    :return: List of clusters as np.arrays
    :rtype: list
    """

    # Convert to index if bool
    if a.dtype == np.bool:
        a = np.flatnonzero(a)

    # Walk through array and find clusters
    da = np.diff(a)
    clusters = []
    current_cluster_size = 1
    for i in range(1, len(a)):
        if da[i-1] > allowed_jump + 1:
            if current_cluster_size >= min_size:
                clusters.append(a[i-current_cluster_size:i])
            current_cluster_size = 1
        else:
            current_cluster_size += 1
    if current_cluster_size >= min_size:
        clusters.append(a[len(a) - current_cluster_size:])

    return clusters


def morph(kind, image, strel_shape, strel_kind='rect'):
    """
    Wrapper for the different opencv morphology operations. Will also work on int/bool images and 1d vectors.
    :param kind: Which morpohological operation to perform. Possibilities are: 'erode', 'dilate', 'open', 'close',
    'gradient', 'tophat', 'whitehat', 'blackhat'.
    :type kind: str
    :param image: Source image to operate on.
    :type image: np.core.multiarray.ndarray
    :param strel_shape: Shape of kernel / structural element.
    :type strel_shape: Union[list, tuple, np.core.multiarray.ndarray, int]
    :param strel_kind: kernel / structural element type. Possibilities are: 'rect', 'cross', 'ellipse', 'circle_big',
    'circle_small'.
    :type strel_kind: str
    :return: Image after morphology operation.
    :rtype: np.core.multiarray.ndarray
    """
    assert kind in ['erode', 'dilate', 'open', 'close', 'gradient', 'tophat', 'whitehat', 'blackhat']
    assert strel_kind in ['rect', 'cross', 'ellipse', 'circle_big', 'circle_small']
    is_image_bool = image.dtype == np.bool
    is_image_int = image.dtype == np.int
    is_image_1d = len(image.shape) == 1
    if not isinstance(strel_shape, tuple):
        strel_shape = tuple(strel_shape if hasattr(strel_shape, '__iter__') else [strel_shape])

    if is_image_bool:
        image = image.astype(np.uint8)
    if is_image_int:
        image = image.astype(np.float)
    if is_image_1d:
        image = image[:, np.newaxis]
        if len(strel_shape) == 1:
            strel_shape = (1, strel_shape[0])

    if strel_kind in ['circle_big', 'circle_small']:
        kernel = circular_structuring_element(strel_shape[0], strel_kind == 'circle_big')
    else:
        strel_types = {'rect': cv2.MORPH_RECT, 'cross': cv2.MORPH_RECT, 'ellipse': cv2.MORPH_ELLIPSE}
        kernel = cv2.getStructuringElement(strel_types[strel_kind], strel_shape)
    if kind == 'erode':
        out = cv2.erode(image, kernel)
    elif kind == 'dilate':
        out = cv2.dilate(image, kernel)
    else:
        op = {'open': cv2.MORPH_OPEN, 'close': cv2.MORPH_CLOSE, 'gradient': cv2.MORPH_GRADIENT,
              'tophat': cv2.MORPH_TOPHAT, 'whitehat': cv2.MORPH_TOPHAT, 'blackhat': cv2.MORPH_BLACKHAT}
        out = cv2.morphologyEx(image, op[kind], kernel)

    if is_image_bool:
        out = out.astype(np.bool)
    elif is_image_int:
        out = intr(out)
    if is_image_1d:
        out = out[:, 0]
    return out


def rolling_window(a, window):
    """
    Split array into rolling window components, e.g. [3,4,5] , window=2 -> [[3,4], [4,5]]
    :param a: Array to split into window size
    :type a: np.core.multiarray.ndarray
    :param window: Window size
    :type window: int
    :return: Array of window arrays
    :rtype: np.core.multiarray.ndarray
    """
    if a.size < window:
        return np.array([])
    return np.lib.stride_tricks.as_strided(a, [a.size + 1 - window, window], (a.strides[0], a.strides[0]))


def bw_edge(mask, include_at_border=False):
    """
    Find edges in binary mask. Edge pixels at the mask borders can optionally be included.
    :param mask: Mask to find edge in
    :type mask: np.core.multiarray.ndarray
    :param include_at_border: Whether to include edges at the border
    :type include_at_border: bool
    :return: Binary edge mask
    :rtype: np.core.multiarray.ndarray
    """
    mask = mask.astype(np.uint8)
    kernel3 = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    edge_mask = cv2.bitwise_xor(mask, cv2.erode(mask, kernel3))
    if include_at_border:
        edge_mask[:, [0, -1]] = mask[:, [0, -1]]
        edge_mask[[0, -1], :] = mask[[0, -1], :]
    return edge_mask.astype(np.bool)


def bw_reconstruct(marker, mask):
    """
    Performs morphological reconstruction of the image marker under the image mask. Inspired by MATLABs bwreconstruct.
    [1, 1, 0]   [0, 0, 0]    [0, 0, 0]
    [0, 0, 0] , [0, 0, 0] -> [0, 0, 0]
    [1, 1, 1]   [0, 1, 0]    [1, 1, 1]
    :param marker: Binary mask indicating which of masks connected components to keep.
    :type marker: np.core.multiarray.ndarray
    :param mask: Binary mask with connected components which are filtered.
    :type mask: np.core.multiarray.ndarray
    :return: Filtered binary mask
    :rtype: np.core.multiarray.ndarray
    """
    areas_num, labels = cv2.connectedComponents(mask.astype(np.uint8))
    labels_to_keep = np.unique(labels[marker.astype(np.bool)])
    labels_to_keep = labels_to_keep[1:] if labels_to_keep.size and labels_to_keep[0] == 0 else labels_to_keep
    out_mask = isin(labels, labels_to_keep)
    return out_mask


def cc_masks(mask):
    """
    Extract each connected component (cc) in its own image and return the array of these images
    :param mask: Binary mask to split into array with each cc separated
    :type mask: np.core.multiarray.ndarray
    :return: Array of separate cc
    :rtype: np.core.multiarray.ndarray
    """
    areas_num, labels = cv2.connectedComponents(mask.astype(np.uint8))
    cc_stack = np.zeros((areas_num - 1, labels.shape[0], labels.shape[1]), np.bool)
    i_cor, j_cor = np.meshgrid(np.arange(labels.shape[0]), np.arange(labels.shape[1]), indexing='ij')
    mask = mask.astype(np.bool)
    cc_stack[labels[mask] - 1, i_cor[mask], j_cor[mask]] = True
    return cc_stack, labels


def bw_area_filter(mask, n=1, area_range=(0, np.inf), output='both'):
    """
    Filter objects from binary mask based on their size. Function can output both filtered mask and/or list of areas.
    :param mask: Binary mask to filter
    :type mask: np.core.multiarray.ndarray
    :param n: Number of largest connected components to keep for components inside area range
    :type n: int
    :param area_range: Range of acceptable areas to keep
    :type area_range: tuple
    :param output: String of what to output. Can either be 'both', 'area', or 'mask'.
    :param output: str
    :return: List of area or mask or tuple of both. All after filtering
    :rtype: Union[int, list, np.core.multiarray.ndarray]
    """
    assert mask.size, "Mask must have non-zero size"

    cc_stack, labels = cc_masks(mask)
    areas = np.bincount(labels[labels > 0])[1:]
    inside_range_idx = np.flatnonzero((areas >= area_range[0]) & (areas <= area_range[1]))
    areas = areas[inside_range_idx]
    keep_idx = np.argsort(areas)[::-1][0:n]
    keep_areas = areas[keep_idx]
    if np.size(keep_areas) == 0:
        keep_areas = np.array([0])
    if n == 1:
        keep_areas = keep_areas[0]
    if output == 'area':
        return keep_areas
    keep_mask = np.any(cc_stack[inside_range_idx[keep_idx], ...], 0)
    if output == 'mask':
        return keep_mask
    return keep_mask, keep_areas


def bw_fill(mask):
    """
    Close interior holes in binary mask.
    :param mask: Binary mask to fill
    :type mask: np.core.multiarray.ndarray
    :return: Filled binary mask
    :rtype: np.core.multiarray.ndarray
    """
    mask_out, contour, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contour:
        cv2.drawContours(mask_out, [cnt], 0, 255, -1)
    return mask_out.astype(np.bool)


def bw_clear_border(mask):
    """
    Remove any connected components touching the image border.
    :param mask: Binary mask to filter
    :type mask: np.core.multiarray.ndarray
    :return: Filtered binary mask
    :rtype: np.core.multiarray.ndarray
    """
    marker = np.zeros_like(mask)
    marker[(0, -1), :] = marker[:, (0, -1)] = True
    return mask ^ bw_reconstruct(marker, mask)


def find(a, if_none=np.nan):
    """
    Similar to np.flatnonzero but if no True elements in a, then find return np.array([if_none]) so find(a)[0] still
    works.
    :param a: Array from which True indexes are return
    :type a: np.core.multiarray.ndarray
    :param if_none: Element or fake-index to return if no True elements in a
    :type if_none: float
    :return: Array with indexes
    :rtype: np.core.multiarray.ndarray
    """
    a_idx = np.flatnonzero(a)
    return a_idx if a_idx.size else np.array([if_none])


def intr(a):
    """
    Round and convert to integer. Especially useful for indexing.
    :param a: Array or float to round and cast
    :type a: Union[float, np.core.multiarray.ndarray]
    :return: Rounded integer or array of ints
    :rtype: Union[float, np.core.multiarray.ndarray]
    """
    return np.round(a).astype(np.int) if isinstance(a, np.ndarray) else int(round(a))


def argmin_nd(a):
    """
    Argmin on multidimensional array. E.g. for a 2D array the output is the (i, j) minimum index.
    :param a: Array to find minimum in
    :type a: np.core.multiarray.ndarray
    :return: Minimum (i, j, ...) index
    :rtype: tuple
    """
    return np.unravel_index(a.argmin(), a.shape)


def argmax_nd(a):
    """
    Argmax on multidimensional array. E.g. for a 2D array the output is the (i, j) maximum index.
    :param a: Array to find maximum in
    :type a: np.core.multiarray.ndarray
    :return: Maximum (i, j, ...) index
    :rtype: tuple
    """
    return np.unravel_index(a.argmax(), a.shape)


def imgradient(img):
    """
    Calculates the (Sobel) gradient magnitude of the image.
    :param img: Image from which to cacluate gradients
    :type img: np.core.multiarray.ndarray
    :return: Gradient magnitude image
    :rtype: np.core.multiarray.ndarray
    """
    return np.sqrt(cv2.Sobel(img, cv2.CV_64F, 1, 0) ** 2 + cv2.Sobel(img, cv2.CV_64F, 0, 1) ** 2)


def curve_step(curve, begin_level, end_level):
    """
    Find the best index to split a curve into a step function based on lowest RMSE.
    :param curve: Curve to look for step in
    :type curve: np.core.multiarray.ndarray
    :param begin_level: Begin value of step function to fit
    :type begin_level: float
    :param end_level: End value of step function to fit
    :type end_level: float
    :return: Curve index where step function goes from begin_level to end_level
    :rtype: int
    """
    cost = np.array([np.sum((curve[:i] - begin_level)**2) + np.sum((curve[i:] - end_level)**2) for i in range(curve.size)])
    return cost.argmin()


def uv_coordinates(matrix, indexing='uv'):
    """
    Get coordinate matrixes with same size as input matrix. Coordinate matrix can either be uv or ij.
    :param matrix: Array whose shape will be used to determine coordinate matrix sizes.
    :type matrix: np.core.multiarray.ndarray
    :param indexing: String or either 'uv' or 'ij'
    :type indexing: str
    :return: Tuple of index matrices
    :rtype: tuple
    """
    if indexing == 'ij':
        return np.meshgrid(np.arange(matrix.shape[0]), np.arange(matrix.shape[1]), indexing='ij')
    return np.meshgrid(np.arange(matrix.shape[1]), np.arange(matrix.shape[0]))


def simple_rotate(image, angle, out='rot_image'):
    """
    Rotate image without cropping it. Rotation is clockwise. simple_rotate can output multitple intermediates so
    "out" can be rot_matrix, rot_function, rot_image or tuple/list of these.
    :param image: Image to rotate
    :type image: np.core.multiarray.ndarray
    :param angle: Angle to rotate
    :type angle: float
    :param out: List (of strings) or string of what to output. Possibilities are:  rot_matrix, rot_function, rot_image
    :type out: Union[list, str]
    :return: Rotated image, roated matrix or rotate function based on "out"
    :rtype: Union[np.core.multiarray.ndarray, list, function]
    """
    out = [out] if isinstance(out, str) else out
    output = []
    # grab the dimensions of the image and then determine the center
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # grab the rotation matrix (applying the negative of the angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    rotate_matrix = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    if 'rot_matrix' in out:
        output.append(rotate_matrix)
        if len(output) == len(out):
            return rotate_matrix
    cos = np.abs(rotate_matrix[0, 0])
    sin = np.abs(rotate_matrix[0, 1])
    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))
    # adjust the rotation matrix to take into account translation
    rotate_matrix[0, 2] += (nW / 2) - cX
    rotate_matrix[1, 2] += (nH / 2) - cY
    # define rotation function, rotate and return
    rotate_function = lambda img: cv2.warpAffine(img.astype(np.uint8), rotate_matrix, (nW, nH)).astype(img.dtype)
    if 'rot_function' in out:
        output.append(rotate_function)
        if len(output) == len(out):
            return output if len(out) > 1 else rotate_function
    rot_img = rotate_function(image)
    if 'rot_image' in out:
        output.append(rot_img)
        return output if len(out) > 1 else rot_img
    return output


def image_crop(image, point, sides, is_point_center=False, indexing='ij', assign=None):
    """
    Cropped an image based on side length and either midpoint or lower-left-corner point. Possibly assign to this sub
    image instead of returning the crop.
    :param image: Image to crop
    :type image: np.core.multiarray.ndarray
    :param point: Anchor point for crop. Point can either be lower-left-corner (i.e. lowest index each side) (default)
    or mid point of crop.
    :type point: Union[list, tuple, np.core.multiarray.ndarray]
    :param sides: Side length of crop. Sides can be negative. Meaning anchor is now lower-left-corner.
    :type sides: Union[list, tuple, np.core.multiarray.ndarray]
    :param is_point_center: Whether anchor point is crop center or lower-left-corner (default)
    :type is_point_center: bool
    :param indexing: Whether to use 'ij' (default) or 'uv' indexing.
    :type indexing: str
    :param assign: If this is not None, this will be assigned to the image crop. In this case the function returns None.
    :type assign: Union[NoneType, np.core.multiarray.ndarray]
    :return: Crop of image.
    :rtype: Union[NoneType, np.core.multiarray.ndarray]
    """
    assert len(point) == len(sides) == 2 and image.ndim >= 2 and indexing in ['ij', 'uv']

    point, sides = np.array(point), np.array(sides)
    if is_point_center:
        point[0] = max(0, point[0] - sides[0] // 2)
        point[1] = max(0, point[1] - sides[1] // 2)
    point, sides = intr(point), intr(sides)

    i = [point[0], point[0] + sides[0]] if sides[0] >= 0 else [max(0, point[0] + sides[0] + 1), point[0] + 1]
    j = [point[1], point[1] + sides[1]] if sides[1] >= 0 else [max(0, point[1] + sides[1] + 1), point[1] + 1]

    if indexing == 'uv':
        i, j = j, i

    if assign is None:
        return image[i[0]: i[1], j[0]: j[1], ...]
    image[i[0]: i[1], j[0]: j[1], ...] = assign


def isin(element, test_elements, assume_unique=False, invert=False):
    """ Equivalent to numpy.isin. Read as is-in. """
    element = np.asarray(element)
    return np.in1d(element, test_elements, assume_unique=assume_unique, invert=invert).reshape(element.shape)


def circular_structuring_element(kernel_size, go_big=False):
    # Create a _symmetrical_ circular structuring element (unlike OpenCV's built-in circular structuring element)
    assert (kernel_size % 2 == 1)  # Only for odd kernel sizes
    kernel1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    kernel2 = kernel1.transpose()
    if go_big:
        kernel = cv2.bitwise_or(kernel1, kernel2)  # Big kernel
    else:
        kernel = cv2.bitwise_and(kernel1, kernel2)  # Small kernel
    return kernel


def showimg(img, cmap="gray", maximize=False):
    """
    Plot an RGB or grayscale image using matplotlib.pyplot

    :param img: Image to plot.
    :type img: np.core.multiarray.ndarray
    :param cmap: Colormap to use if image is 1D. Examples: gray, hot, hot_r, jet, jet_r, summer, rainbow, ...
    :type cmap: str
    :param maximize: Maximize plot window?
    :type maximize: bool
    :return: Figure containing the plotted image
    :rtype: matplotlib.figure.Figure
    """
    import matplotlib.pyplot as plt

    # Figure/window size if not maximized
    figure_width_inches = 18.5
    figure_height_inches = 10.5

    # Window size
    fig = plt.figure()
    fig.set_size_inches(figure_width_inches, figure_height_inches, forward=True)
    # mngr = plt.get_current_fig_manager()  # get the QTCore PyRect object
    # if maximize:
    #     mngr.window.showMaximized()
    # else:
    #     geom = mngr.window.geometry()
    #     x, y, dx, dy = geom.getRect()
    #     fig.set_size_inches(figure_width_inches, figure_height_inches, forward=True)
    #     geom = mngr.window.geometry()
    #     x2, y2, dx2, dy2 = geom.getRect()
    #     new_x = max(2, x + dx / 2 - dx2 / 2)  # Do not move the window (incl. window border) off the screen
    #     new_y = max(39, y + dy / 2 - dy2 / 2)  # Do not move the window (incl. window border) off the screen
    #     mngr.window.setGeometry(new_x, new_y, dx2, dy2)

    # Show image
    if len(img.shape) == 1:
        plt.plot(img)
    elif len(img.shape) <= 2 or img.shape[2] == 1 or cmap is None:
        plt.imshow(img, cmap=cmap, interpolation="none")
    else:
        plt.imshow(img, interpolation="none")

    # Trim margins
    plt.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.02)
    plt.show()

    return fig