"""
Functions to smooth fields
"""
import argparse
import itertools
import math
import multiprocessing
import os
import struct

import matplotlib.pyplot as plt
import numpy as np
from joblib import Parallel, delayed
from scipy.ndimage.filters import gaussian_filter, median_filter

from contour_plots import read_2d_fields
from dolointerpolation import MultilinearInterpolator
from energy_conversion import read_data_from_json


def smooth_interp_emf(run_dir, pic_info, eb_field_name, tframe, coords):
    """
    Smooth electric and magnetic field and also interpolate them to
    grid locations where hydro quantities are.
    """
    kwargs = {"current_time": tframe, "xl": 0, "xr": pic_info.lx_di,
              "zb": -0.5 * pic_info.lz_di, "zt": 0.5 * pic_info.lz_di}
    size_one_frame = pic_info.nx * pic_info.nz * 4
    fname = run_dir + "data/" + eb_field_name + "_original.gda"
    statinfo = os.stat(fname)
    file_size = statinfo.st_size
    if file_size < size_one_frame * (tframe + 1):
        return
    else:
        x, z, fdata = read_2d_fields(pic_info, fname, **kwargs)
    if 'ex' in eb_field_name or 'bz' in eb_field_name:
        f = MultilinearInterpolator(coords["smin_ex_bz"],
                                    coords["smax_ex_bz"],
                                    coords["orders"],
                                    dtype=np.float32)
    elif 'ez' in eb_field_name or 'bx' in eb_field_name:
        f = MultilinearInterpolator(coords["smin_ez_bx"],
                                    coords["smax_ez_bx"],
                                    coords["orders"],
                                    dtype=np.float32)
    elif 'ey' in eb_field_name:
        f = MultilinearInterpolator(coords["smin_h"],
                                    coords["smax_h"],
                                    coords["orders"],
                                    dtype=np.float32)
    else:
        f = MultilinearInterpolator(coords["smin_by"],
                                    coords["smax_by"],
                                    coords["orders"],
                                    dtype=np.float32)
    f.set_values(np.atleast_2d(np.transpose(fdata).flatten()))
    nx = pic_info.nx
    nz = pic_info.nz
    fdata = f(coords["coord"])
    fdata = np.transpose(f(coords["coord"]).reshape((nx, nz)))
    # only smooth electric field
    if any(ename in eb_field_name for ename in ['ex', 'ey', 'ez']):
        sigma = 3
        fdata = gaussian_filter(fdata, sigma)
    fname = run_dir + "data/" + eb_field_name + ".gda"
    with open(fname, 'a+') as f:
        offset = size_one_frame * tframe
        f.seek(offset, os.SEEK_SET)
        fdata.tofile(f)


def smooth_emf(run_dir, pic_info, emf_name, tframe, coords):
    """
    Smooth electric and magnetic field
    """
    kwargs = {"current_time": tframe, "xl": 0, "xr": pic_info.lx_di,
              "zb": -0.5 * pic_info.lz_di, "zt": 0.5 * pic_info.lz_di}
    size_one_frame = pic_info.nx * pic_info.nz * 4
    # fname = run_dir + "data/original_data/" + emf_name + ".gda"
    fname = run_dir + "data1/original_data/" + emf_name + ".gda"
    statinfo = os.stat(fname)
    file_size = statinfo.st_size
    if file_size < size_one_frame * (tframe + 1):
        return
    else:
        x, z, fdata = read_2d_fields(pic_info, fname, **kwargs)
    sigma = 5
    fdata = median_filter(fdata, sigma)
    # fname = run_dir + "data/" + emf_name + ".gda"
    fname = run_dir + "data1/" + emf_name + ".gda"
    with open(fname, 'a+') as f:
        offset = size_one_frame * tframe
        f.seek(offset, os.SEEK_SET)
        fdata.tofile(f)


def check_exb(run_dir, pic_info, tframe):
    """
    Check calculated ExB drift
    """
    kwargs = {"current_time": tframe, "xl": 0, "xr": pic_info.lx_di,
              "zb": -0.5 * pic_info.lz_di, "zt": 0.5 * pic_info.lz_di}
    size_one_frame = pic_info.nx * pic_info.nz * 4
    fname = run_dir + "data1/vexb_x.gda"
    x, z, vexbx1 = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data1/vexb_y.gda"
    x, z, vexby1 = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data1/vexb_z.gda"
    x, z, vexbz1 = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data/ex.gda"
    x, z, ex = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data/ey.gda"
    x, z, ey = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data/ez.gda"
    x, z, ez = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data/bx.gda"
    x, z, bx = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data/by.gda"
    x, z, by = read_2d_fields(pic_info, fname, **kwargs)
    fname = run_dir + "data/bz.gda"
    x, z, bz = read_2d_fields(pic_info, fname, **kwargs)
    ib2 = 1.0 / (bx**2 + by**2 + bz**2)
    vexbx2 = (ey * bz - ez * by) * ib2
    vexby2 = (ez * bx - ex * bz) * ib2
    vexbz2 = (ex * by - ey * bx) * ib2
    p1 = plt.imshow(vexbz2 - vexbz1, cmap=plt.cm.jet,
                    # extent=[xmin, xmax, zmin, zmax],
                    # vmin=vmin, vmax=vmax,
                    aspect='auto', origin='lower',
                    interpolation='bicubic')
    plt.show()


def get_coordinates(pic_info):
    """Get the coordinates where the fields are
    """
    smime = math.sqrt(pic_info.mime)
    dx = pic_info.dx_di * smime
    dz = pic_info.dz_di * smime
    dxh = dx * 0.5
    dzh = dz * 0.5
    nx_pic = pic_info.nx
    nz_pic = pic_info.nz
    lx_pic = pic_info.lx_di * smime
    lz_pic = pic_info.lz_di * smime
    x1 = np.linspace(-dxh, lx_pic + dxh, nx_pic + 2)
    x2 = np.linspace(-dx, lx_pic, nx_pic + 2)
    z1 = np.linspace(-dzh - 0.5 * lz_pic, 0.5 * lz_pic + dzh, nz_pic + 2)
    z2 = np.linspace(-dz - 0.5 * lz_pic, 0.5 * lz_pic, nz_pic + 2)
    points_x, points_z = np.broadcast_arrays(x2[1:-1].reshape(-1,1), z2[1:-1])
    coord = np.vstack((points_x.flatten(), points_z.flatten()))
    orders = [nx_pic, nz_pic]
    smin_h = [x2[1], z2[1]]         # for hydro, Ey
    smax_h = [x2[-2], z2[-2]]
    smin_ex_bz = [x1[1], z2[1]]     # for Ex, Bz
    smax_ex_bz = [x1[-2], z2[-2]]
    smin_ez_bx = [x2[1], z1[1]]     # for Ez, Bx
    smax_ez_bx = [x2[-2], z1[-2]]
    smin_by = [x1[1], z1[1]]        # for By
    smax_by = [x1[-2], z1[-2]]

    coords = {"coord": coord, "orders": orders, "smin_h": smin_h,
              "smax_h": smax_h, "smin_ex_bz": smin_ex_bz,
              "smax_ex_bz": smax_ex_bz, "smin_ez_bx": smin_ez_bx,
              "smax_ez_bx": smax_ez_bx, "smin_by": smin_by,
              "smax_by": smax_by}

    return coords


def get_cmd_args():
    """Get command line arguments
    """
    default_run_name = 'mime25_beta002_bg00'
    default_run_dir = ('/net/scratch3/xiaocanli/reconnection/mime25/' +
                       default_run_name + '/')
    parser = argparse.ArgumentParser(description='Smooth fields')
    parser.add_argument('--species', action="store", default='e',
                        help='particle species')
    parser.add_argument('--run_dir', action="store", default=default_run_dir,
                        help='run directory')
    parser.add_argument('--run_name', action="store", default=default_run_name,
                        help='run name')
    return parser.parse_args()


if __name__ == "__main__":
    args = get_cmd_args()
    run_name = args.run_name
    run_dir = args.run_dir
    picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
    pic_info = read_data_from_json(picinfo_fname)
    coords = get_coordinates(pic_info)
    tframes = range(pic_info.ntf)
    # runs_root_dir = "/net/scratch3/xiaocanli/reconnection/frequent_dump/"
    # run_names = ["mime25_beta002_guide00_frequent_dump",
    #              "mime25_beta002_guide02_frequent_dump",
    #              "mime25_beta002_guide05_frequent_dump",
    #              "mime25_beta002_guide10_frequent_dump",
    #              "mime25_beta008_guide00_frequent_dump",
    #              "mime25_beta032_guide00_frequent_dump"]
    runs_root_dir = "/net/scratch3/xiaocanli/reconnection/mime25/"
    run_names = ["mime25_beta002_bg00"]
    # enames = ["ex", "ey", "ez"]
    # enames = ["bx", "by", "bz"]
    enames = ["vexb_x", "vexb_y", "vexb_z"]
    suffixs = ["", "_pre", "_post"]
    efield_names = [ename + suffixs for ename, suffixs in
                    itertools.product(enames, suffixs)]
    run_efields = [{"run_name": run_name, "efield_name": efield_name}
                   for run_name, efield_name
                   in itertools.product(run_names, efield_names)]
    # smooth_interp_emf(run_dir, pic_info, 'ex', 10, coords)
    # for tframe in range(10):
    #     smooth_interp_emf(run_dir, pic_info, 'ex', tframe, coords)
    # check_exb(run_dir, pic_info, 50)
    def processInput(run_efield):
        run_name = run_efield["run_name"]
        picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
        pic_info = read_data_from_json(picinfo_fname)
        coords = get_coordinates(pic_info)
        tframes = range(pic_info.ntf)
        efield_name = run_efield["efield_name"]
        print("Run name and electric field name: %s %s" % (run_name, efield_name))
        run_dir = runs_root_dir + run_name + '/'
        for tframe in tframes:
            # smooth_interp_emf(run_dir, pic_info, efield_name, tframe, coords)
            smooth_emf(run_dir, pic_info, efield_name, tframe, coords)
    ncores = multiprocessing.cpu_count()
    Parallel(n_jobs=ncores)(delayed(processInput)(run_efield)
                            for run_efield in run_efields)
