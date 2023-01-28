from tqdm import trange
import numpy as np
import matplotlib.pyplot as plt

def window3x3(arr, shape=(3, 3)):
    r_win = np.floor(shape[0] / 2).astype(int)
    c_win = np.floor(shape[1] / 2).astype(int)
    x, y = arr.shape
    for i in range(x):
        xmin = max(0, i - r_win)
        xmax = min(x, i + r_win + 1)
        for j in range(y):
            ymin = max(0, j - c_win)
            ymax = min(y, j + c_win + 1)
            yield arr[xmin:xmax, ymin:ymax]


def gradient(XYZ_file, min=0, max=15, figsize=(6, 8), **kwargs):

    """

    :param XYZ_file: XYZ file in the following format: x,y,z (including headers)
    :param min: color bar minimum range.
    :param max: color bar maximum range.
    :param figsize: figure size.
    :param kwargs:
           plot: to plot a gradient map. Default is True.
    :return: returns an array with the shape of the grid with the computed slopes


    The algorithm calculates the gradient using a first-order forward or backward difference on the corner points, first
    order central differences at the boarder points, and a 3x3 moving window for every cell with 8 surrounding cells (in
    the middle of the grid) using a third-order finite difference weighted by reciprocal of squared distance

    Assumed 3x3 window:

                        -------------------------
                        |   a   |   b   |   c   |
                        -------------------------
                        |   d   |   e   |   f   |
                        -------------------------
                        |   g   |   h   |   i   |
                        -------------------------


    """

    kwargs.setdefault('plot', True)

    grid = XYZ_file.to_numpy()

    nx = XYZ_file.iloc[:,0].unique().size
    ny = XYZ_file.iloc[:,1].unique().size

    xs = grid[:, 0].reshape(ny, nx, order='A')
    ys = grid[:, 1].reshape(ny, nx, order='A')
    zs = grid[:, 2].reshape(ny, nx, order='A')
    dx = abs((xs[:, 1:] - xs[:, :-1]).mean())
    dy = abs((ys[1:, :] - ys[:-1, :]).mean())

    gen = window3x3(zs)
    windows_3x3 = np.asarray(list(gen))
    windows_3x3 = windows_3x3.reshape(ny, nx)

    dzdx = np.empty((ny, nx))
    dzdy = np.empty((ny, nx))
    loc_string = np.empty((ny, nx), dtype="S25")

    for ax_y in trange(ny):
        for ax_x in range(nx):

            # corner points
            if ax_x == 0 and ax_y == 0:  # top left corner
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][0][1] - windows_3x3[ax_y, ax_x][0][0]) / dx
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][0] - windows_3x3[ax_y, ax_x][0][0]) / dy
                loc_string[ax_y, ax_x] = 'top left corner'

            elif ax_x == nx - 1 and ax_y == 0:  # top right corner
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][0][1] - windows_3x3[ax_y, ax_x][0][0]) / dx
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][0][1]) / dy
                loc_string[ax_y, ax_x] = 'top right corner'

            elif ax_x == 0 and ax_y == ny - 1:  # bottom left corner
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][1][0]) / dx
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][0] - windows_3x3[ax_y, ax_x][0][0]) / dy
                loc_string[ax_y, ax_x] = 'bottom left corner'

            elif ax_x == nx - 1 and ax_y == ny - 1:  # bottom right corner
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][1][0]) / dx
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][0][1]) / dy
                loc_string[ax_y, ax_x] = 'bottom right corner'

            # top boarder
            elif (ax_y == 0) and (ax_x != 0 and ax_x != nx - 1):
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][0][-1] - windows_3x3[ax_y, ax_x][0][0]) / (2 * dx)
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][0][1]) / dy
                loc_string[ax_y, ax_x] = 'top boarder'

            # bottom boarder
            elif ax_y == ny - 1 and (ax_x != 0 and ax_x != nx - 1):
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][-1] - windows_3x3[ax_y, ax_x][1][0]) / (2 * dx)
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][0][1]) / dy
                loc_string[ax_y, ax_x] = 'bottom boarder'

            # left boarder
            elif ax_x == 0 and (ax_y != 0 and ax_y != ny - 1):
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][1][0]) / dx
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][-1][0] - windows_3x3[ax_y, ax_x][0][0]) / (2 * dy)
                loc_string[ax_y, ax_x] = 'left boarder'

            # right boarder
            elif ax_x == nx - 1 and (ax_y != 0 and ax_y != ny - 1):
                dzdx[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][1][1] - windows_3x3[ax_y, ax_x][1][0]) / dx
                dzdy[ax_y, ax_x] = (windows_3x3[ax_y, ax_x][-1][-1] - windows_3x3[ax_y, ax_x][0][-1]) / (2 * dy)
                loc_string[ax_y, ax_x] = 'right boarder'

            # middle grid
            else:
                a = windows_3x3[ax_y, ax_x][0][0]
                b = windows_3x3[ax_y, ax_x][0][1]
                c = windows_3x3[ax_y, ax_x][0][-1]
                d = windows_3x3[ax_y, ax_x][1][0]
                f = windows_3x3[ax_y, ax_x][1][-1]
                g = windows_3x3[ax_y, ax_x][-1][0]
                h = windows_3x3[ax_y, ax_x][-1][1]
                i = windows_3x3[ax_y, ax_x][-1][-1]

                dzdx[ax_y, ax_x] = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * dx)
                dzdy[ax_y, ax_x] = ((g + 2 * h + i) - (a + 2 * b + c)) / (8 * dy)
                loc_string[ax_y, ax_x] = 'middle grid'

    hpot = np.hypot(abs(dzdy), abs(dzdx))
    slopes_angle = np.degrees(np.arctan(hpot))
    if kwargs['plot']:
        slopes_angle[(slopes_angle < min) | (slopes_angle > max)]

        plt.figure(figsize=figsize)
        plt.pcolormesh(xs, ys, slopes_angle, cmap='Greys', vmax=max, vmin=min)

        plt.colorbar()
        plt.tight_layout()
        plt.show()

    return slopes_angle, xs, ys


def hillshade(array, azimuth, angle_altitude):

    x, y = np.gradient(array)
    slope = np.pi / 2. - np.arctan(np.sqrt(x * x + y * y))
    aspect = np.arctan2(-x, y)
    azimuthrad = azimuth * np.pi / 180.
    altituderad = angle_altitude * np.pi / 180.

    shaded = np.sin(altituderad) * np.sin(slope) \
             + np.cos(altituderad) * np.cos(slope) \
             * np.cos(azimuthrad - aspect)
    hillshade_array = 255 * (shaded + 1) / 2

    return hillshade_array
