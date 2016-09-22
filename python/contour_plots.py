"""
Analysis procedures for 2D contour plots.
"""
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import LogNorm
from matplotlib import rc
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
from scipy.ndimage.filters import generic_filter as gf
from scipy import signal
from scipy.fftpack import fft2, ifft2, fftshift
import math
import os.path
import struct
import collections
import pic_information
import color_maps as cm
import colormap.colormaps as cmaps
from runs_name_path import ApJ_long_paper_runs
from energy_conversion import read_data_from_json
from shell_functions import mkdir_p
from joblib import Parallel, delayed
import multiprocessing

rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
mpl.rc('text', usetex=True)
mpl.rcParams['text.latex.preamble'] = [r"\usepackage{amsmath}"]

font = {'family' : 'serif',
        #'color'  : 'darkred',
        'color'  : 'black',
        'weight' : 'normal',
        'size'   : 24,
        }
mpl.rcParams['contour.negative_linestyle'] = 'solid'

def read_2d_fields(pic_info, fname, current_time, xl, xr, zb, zt):
    """Read 2D fields data from file.
    
    Args:
        pic_info: namedtuple for the PIC simulation information.
        fname: the filename.
        current_time: current time frame.
        xl, xr: left and right x position in di (ion skin length).
        zb, zt: top and bottom z position in di.
    """
    print 'Reading data from ', fname
    print 'The spatial range (di): ', \
            'x_left = ', xl, 'x_right = ', xr, \
            'z_bottom = ', zb, 'z_top = ', zt
    nx = pic_info.nx
    nz = pic_info.nz
    x_di = pic_info.x_di
    z_di = pic_info.z_di
    dx_di = pic_info.dx_di
    dz_di = pic_info.dz_di
    xmin = np.min(x_di)
    xmax = np.max(x_di)
    zmin = np.min(z_di)
    zmax = np.max(z_di)
    if (xl <= xmin):
        xl_index = 0
    else:
        xl_index = int(math.floor((xl-xmin) / dx_di))
    if (xr >= xmax):
        xr_index = nx - 1
    else:
        xr_index = int(math.ceil((xr-xmin) / dx_di))
    if (zb <= zmin):
        zb_index = 0
    else:
        zb_index = int(math.floor((zb-zmin) / dz_di))
    if (zt >= zmax):
        zt_index = nz - 1
    else:
        zt_index = int(math.ceil((zt-zmin) / dz_di))
    nx1 = xr_index-xl_index+1
    nz1 = zt_index-zb_index+1
    fp = np.zeros((nz1, nx1))
    offset = nx*nz*current_time*4 + zb_index*nx*4 + xl_index*4
    for k in range(nz1):
        fp[k, :] = np.memmap(fname, dtype='float32', mode='r', 
                offset=offset, shape=(nx1), order='F')
        offset += nx * 4
    return (x_di[xl_index:xr_index+1], z_di[zb_index:zt_index+1], fp)

def plot_2d_contour(x, z, field_data, ax, fig, is_cbar=1, **kwargs):
    """Plot contour of 2D fields.

    Args:
        x, z: the x and z coordinates for the field data.
        field_data: the 2D field data set.
        ax: axes object.
        fig: figure object.
        is_cbar: whether to plot colorbar. Default is yes.
    Returns:
        p1: plot object.
        cbar: color bar object.
    """
    xmin = np.min(x)
    xmax = np.max(x)
    zmin = np.min(z)
    zmax = np.max(z)
    nx, = x.shape
    nz, = z.shape
    if (kwargs and "xstep" in kwargs and "zstep" in kwargs):
        data = field_data[0:nz:kwargs["zstep"], 0:nx:kwargs["xstep"]]
    else:
        data = field_data
    print "Maximum and minimum of the data: ", np.max(data), np.min(data)
    if (kwargs and "vmin" in kwargs and "vmax" in kwargs):
        p1 = ax.imshow(data, cmap=plt.cm.jet,
                extent=[xmin, xmax, zmin, zmax],
                aspect='auto', origin='lower',
                vmin=kwargs["vmin"], vmax=kwargs["vmax"],
                interpolation='bicubic')
    else:
        p1 = ax.imshow(data, cmap=plt.cm.jet,
                extent=[xmin, xmax, zmin, zmax],
                aspect='auto',
                origin='lower',
                interpolation='spline16')
    # Log scale plot
    if (kwargs and "is_log" in kwargs and kwargs["is_log"] == True):
        p1.norm=LogNorm(vmin=kwargs["vmin"], vmax=kwargs["vmax"])
    ax.tick_params(labelsize=16)
    ax.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    #ax.set_title(r'$\beta_e$', fontsize=24)

    if is_cbar == 1:
        # create an axes on the right side of ax. The width of cax will be 5%
        # of ax and the padding between cax and ax will be fixed at 0.05 inch.
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.05)
        cbar = fig.colorbar(p1, cax=cax)
        cbar.ax.tick_params(labelsize=16)
        return (p1, cbar)
    else:
        return p1

def plot_jy(pic_info, species, current_time):
    """Plot out-of-plane current density.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-20, "zt":20}
    x, z, jy = read_2d_fields(pic_info, "../../data/jy.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.5, "vmax":0.5}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, jy, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    # p1.set_cmap(cmaps.inferno)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    cbar1.ax.set_ylabel(r'$j_y$', fontdict=font, fontsize=24)
    cbar1.set_ticks(np.arange(-0.4, 0.5, 0.2))
    cbar1.ax.tick_params(labelsize=24)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir('../img/img_jy2/'):
        os.makedirs('../img/img_jy2/')
    fname = '../img/img_jy2/jy_' + species + '_' + \
            str(current_time).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=200)

    plt.show()
    # plt.close()

def plot_absB_jy(pic_info, species, current_time):
    """Plot magnetic field strength and out-of-plane current density.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-30, "zt":30}
    x, z, jy = read_2d_fields(pic_info, "../../data/jy.gda", **kwargs) 
    x, z, absB = read_2d_fields(pic_info, "../../data/absB.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.8
    height = 0.37
    xs = 0.12
    ys = 0.92 - height
    gap = 0.05
    fig = plt.figure(figsize=[7, 5])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":0, "vmax":2.0}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, absB, ax1, fig, **kwargs_plot)
    # p1.set_cmap(plt.cm.get_cmap('seismic'))
    p1.set_cmap(cmaps.plasma)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax1.tick_params(labelsize=16)
    ax1.tick_params(axis='x', labelbottom='off')
    # cbar1.set_ticks(np.arange(0, 1.0, 0.2))
    cbar1.ax.tick_params(labelsize=16)
    ax1.text(0.02, 0.8, r'$|\mathbf{B}|$', color='w', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.5, "vmax":0.5}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p2, cbar2 = plot_2d_contour(x, z, jy, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.get_cmap('seismic'))
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax2.tick_params(labelsize=16)
    cbar2.set_ticks(np.arange(-0.4, 0.5, 0.2))
    cbar2.ax.tick_params(labelsize=16)
    ax2.text(0.02, 0.8, r'$j_y$', color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=20)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    dir = '../img/img_absB_jy/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    fname = dir + 'absB_jy_' + str(current_time).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=200)

    # plt.show()
    plt.close()


def plot_by_multi():
    """Plot out-of-plane magnetic field for multiple runs.
    """
    base_dirs, run_names = ApJ_long_paper_runs()
    print run_names
    ct1, ct2, ct3 = 20, 21, 11
    kwargs = {"current_time":ct1, "xl":0, "xr":200, "zb":-10, "zt":10}
    base_dir = base_dirs[2]
    run_name = run_names[2]
    picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
    pic_info = read_data_from_json(picinfo_fname)
    fname1 = base_dir + 'data/jy.gda'
    fname2 = base_dir + 'data/Ay.gda'
    x, z, by1 = read_2d_fields(pic_info, fname1, **kwargs) 
    x, z, Ay1 = read_2d_fields(pic_info, fname2, **kwargs) 
    kwargs["current_time"] = ct2
    base_dir = base_dirs[5]
    run_name = run_names[5]
    picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
    pic_info = read_data_from_json(picinfo_fname)
    fname1 = base_dir + 'data/by.gda'
    fname2 = base_dir + 'data/Ay.gda'
    x, z, by2 = read_2d_fields(pic_info, fname1, **kwargs) 
    x, z, Ay2 = read_2d_fields(pic_info, fname2, **kwargs) 
    kwargs["current_time"] = ct3
    base_dir = base_dirs[6]
    run_name = run_names[6]
    picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
    pic_info = read_data_from_json(picinfo_fname)
    fname1 = base_dir + 'data/by.gda'
    fname2 = base_dir + 'data/Ay.gda'
    x, z, by3 = read_2d_fields(pic_info, fname1, **kwargs) 
    x, z, Ay3 = read_2d_fields(pic_info, fname2, **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.24
    gap = 0.05
    xs = 0.12
    ys = 0.96 - height
    w1, h1 = 7, 5
    fig = plt.figure(figsize=[w1, h1])

    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-1.0, "vmax":1.0}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1 = plot_2d_contour(x, z, by1, ax1, fig, is_cbar=0, **kwargs_plot)
    xs1 = xs + width*1.02
    ys1 = ys - 2*(height + gap)
    width1 = width*0.04
    height1 = 3*height + 2*gap
    cax = fig.add_axes([xs1, ys1, width1, height1])
    cbar1 = fig.colorbar(p1, cax=cax)
    cbar1.ax.tick_params(labelsize=16)
    p1.set_cmap(plt.cm.get_cmap('bwr'))
    levels = np.linspace(np.max(Ay1), np.min(Ay1), 10)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay1[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5, levels=levels)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax1.tick_params(labelsize=16)
    ax1.tick_params(axis='x', labelbottom='off')
    cbar1.set_ticks(np.arange(-0.8, 0.9, 0.4))
    cbar1.ax.tick_params(labelsize=16)
    t_wci = ct1*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.text(0.02, 0.8, title, color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    p2 = plot_2d_contour(x, z, by2, ax2, fig, is_cbar=0, **kwargs_plot)
    p2.set_cmap(plt.cm.get_cmap('bwr'))
    levels = np.linspace(np.max(Ay2), np.min(Ay2), 10)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay2[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5, levels=levels)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax2.tick_params(labelsize=16)
    ax2.tick_params(axis='x', labelbottom='off')
    t_wci = ct2*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax2.text(0.02, 0.8, title, color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)

    ys -= height + gap
    ax3 = fig.add_axes([xs, ys, width, height])
    p3 = plot_2d_contour(x, z, by3, ax3, fig, is_cbar=0, **kwargs_plot)
    p3.set_cmap(plt.cm.get_cmap('bwr'))
    levels = np.linspace(np.max(Ay3), np.min(Ay3), 10)
    ax3.contour(x[0:nx:xstep], z[0:nz:zstep], Ay3[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5, levels=levels)
    ax3.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax3.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax3.tick_params(labelsize=16)
    t_wci = ct3*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax3.text(0.02, 0.8, title, color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax3.transAxes)

    # minor_ticks = np.arange(0, 200, 5)
    # ax3.set_xticks(minor_ticks, minor=True)
    # ax3.grid(which='both')
    
    # if not os.path.isdir('../img/'):
    #     os.makedirs('../img/')
    # fname = '../img/by_time.eps'
    # fig.savefig(fname)

    plt.show()
    # plt.close()


def plot_by(pic_info):
    """Plot out-of-plane magnetic field.
    """
    ct1, ct2, ct3 = 10, 20, 35
    kwargs = {"current_time":ct1, "xl":0, "xr":200, "zb":-10, "zt":10}
    x, z, by1 = read_2d_fields(pic_info, "../../data/by.gda", **kwargs) 
    x, z, Ay1 = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    kwargs["current_time"] = ct2
    x, z, by2 = read_2d_fields(pic_info, "../../data/by.gda", **kwargs) 
    x, z, Ay2 = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    kwargs["current_time"] = ct3
    x, z, by3 = read_2d_fields(pic_info, "../../data/by.gda", **kwargs) 
    x, z, Ay3 = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.24
    gap = 0.05
    xs = 0.12
    ys = 0.96 - height
    w1, h1 = 7, 5
    fig = plt.figure(figsize=[w1, h1])

    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-1.0, "vmax":1.0}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1 = plot_2d_contour(x, z, by1, ax1, fig, is_cbar=0, **kwargs_plot)
    xs1 = xs + width*1.02
    ys1 = ys - 2*(height + gap)
    width1 = width*0.04
    height1 = 3*height + 2*gap
    cax = fig.add_axes([xs1, ys1, width1, height1])
    cbar1 = fig.colorbar(p1, cax=cax)
    cbar1.ax.tick_params(labelsize=16)
    p1.set_cmap(plt.cm.get_cmap('bwr'))
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay1[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax1.tick_params(labelsize=16)
    ax1.tick_params(axis='x', labelbottom='off')
    cbar1.set_ticks(np.arange(-0.8, 0.9, 0.4))
    cbar1.ax.tick_params(labelsize=16)
    t_wci = ct1*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.text(0.02, 0.8, title, color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    p2 = plot_2d_contour(x, z, by2, ax2, fig, is_cbar=0, **kwargs_plot)
    p2.set_cmap(plt.cm.get_cmap('bwr'))
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay2[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax2.tick_params(labelsize=16)
    ax2.tick_params(axis='x', labelbottom='off')
    t_wci = ct2*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax2.text(0.02, 0.8, title, color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)

    ys -= height + gap
    ax3 = fig.add_axes([xs, ys, width, height])
    p3 = plot_2d_contour(x, z, by3, ax3, fig, is_cbar=0, **kwargs_plot)
    p3.set_cmap(plt.cm.get_cmap('bwr'))
    ax3.contour(x[0:nx:xstep], z[0:nz:zstep], Ay3[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax3.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax3.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax3.tick_params(labelsize=16)
    t_wci = ct3*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax3.text(0.02, 0.8, title, color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax3.transAxes)

    # minor_ticks = np.arange(0, 200, 5)
    # ax3.set_xticks(minor_ticks, minor=True)
    # ax3.grid(which='both')
    
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    fname = '../img/by_time.eps'
    fig.savefig(fname)

    plt.show()
    # plt.close()


def plot_number_density(pic_info, species, ct, run_name, shock_pos,
                        base_dir='../../'):
    """Plot plasma beta and number density.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        ct current time frame.
    """
    xmin, xmax = 0, pic_info.lx_di
    xmax = 105
    zmin, zmax = -0.5*pic_info.lz_di, 0.5*pic_info.lz_di
    kwargs = {"current_time":ct, "xl":xmin, "xr":xmax, "zb":zmin, "zt":zmax}
    fname = base_dir + 'data1/n' + species + '.gda'
    x, z, num_rho = read_2d_fields(pic_info, fname, **kwargs) 
    fname = base_dir + 'data1/Ay.gda'
    x, z, Ay = read_2d_fields(pic_info, fname, **kwargs) 
    nx, = x.shape
    nz, = z.shape
    nrho_cum = np.sum(num_rho, axis=0) / nz
    xm = x[shock_pos]

    w1, h1 = 0.7, 0.52
    xs, ys = 0.15, 0.94 - h1
    gap = 0.05

    width, height = 10, 12
    fig = plt.figure(figsize=[10,12])
    ax1 = fig.add_axes([xs, ys, w1, h1])
    # kwargs_plot = {"xstep":2, "zstep":2, "is_log":True, "vmin":0.1, "vmax":10}
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":0.5, "vmax":5}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, num_rho, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.jet)
    nlevels = 15
    levels = np.linspace(np.min(Ay), np.max(Ay), nlevels)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5, levels=levels)
    ax1.set_xlim([xmin, xmax])
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    lname = r'$n_' + species + '$'
    cbar1.ax.set_ylabel(lname, fontdict=font, fontsize=24)
    cbar1.ax.tick_params(labelsize=24)

    ax1.plot([xm, xm], [zmin, zmax], color='white', linestyle='--')
    
    t_wci = ct*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    h2 = 0.3
    ys -= gap + h2
    w2 = w1 * 0.98 - 0.05 / width
    ax2 = fig.add_axes([xs, ys, w2, h2])
    ax2.plot(x, nrho_cum, linewidth=2, color='k')
    ax2.set_xlim([xmin, xmax])
    ax2.set_ylim([0.5, 4.5])
    ax2.plot([xm, xm], ax2.get_ylim(), color='k', linestyle='--')
    ax2.tick_params(labelsize=24)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)

    fig_dir = '../img/img_number_densities/' + run_name + '/'
    mkdir_p(fig_dir)
    fname = fig_dir + '/nrho_linear_' + species + '_' + str(ct).zfill(3) + '.jpg'
    fig.savefig(fname)

    # plt.show()
    plt.close()


def plot_vx(pic_info, species, ct, run_name, shock_pos, base_dir='../../'):
    """Plot vx

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        ct current time frame.
    """
    xmin, xmax = 0, pic_info.lx_di
    xmax = 105
    zmin, zmax = -0.5*pic_info.lz_di, 0.5*pic_info.lz_di
    kwargs = {"current_time":ct, "xl":xmin, "xr":xmax, "zb":zmin, "zt":zmax}
    fname = base_dir + 'data1/v' + species + 'x.gda'
    x, z, vx = read_2d_fields(pic_info, fname, **kwargs) 
    fname = base_dir + 'data1/Ay.gda'
    x, z, Ay = read_2d_fields(pic_info, fname, **kwargs) 
    nx, = x.shape
    nz, = z.shape
    vx_cum = np.sum(vx, axis=0) / nz
    vx_grad = np.abs(np.gradient(vx_cum))
    xm = x[shock_pos]

    w1, h1 = 0.7, 0.52
    xs, ys = 0.15, 0.94 - h1
    gap = 0.05

    width, height = 10, 12
    fig = plt.figure(figsize=[10,12])
    ax1 = fig.add_axes([xs, ys, w1, h1])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-0.1, "vmax":0.1}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, vx, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.jet)
    nlevels = 20
    levels = np.linspace(np.min(Ay), np.max(Ay), nlevels)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5, levels=levels)
    ax1.set_xlim([xmin, xmax])
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    lname = r'$v_{' + species + 'x}$'
    cbar1.ax.set_ylabel(lname, fontdict=font, fontsize=24)
    cbar1.ax.tick_params(labelsize=24)

    ax1.plot([xm, xm], [zmin, zmax], color='k', linestyle='--')
    
    t_wci = ct*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    h2 = 0.3
    ys -= gap + h2
    w2 = w1 * 0.98 - 0.05 / width
    ax2 = fig.add_axes([xs, ys, w2, h2])
    ax2.plot(x, vx_cum, linewidth=2, color='k')
    ax2.set_xlim([xmin, xmax])
    ax2.set_ylim([-0.25, 0.10])
    ax2.plot([xm, xm], ax2.get_ylim(), color='k', linestyle='--')
    ax2.tick_params(labelsize=24)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)

    fig_dir = '../img/img_velocity/' + run_name + '/'
    mkdir_p(fig_dir)
    fname = fig_dir + '/v' + species + 'x_' + str(ct).zfill(3) + '.jpg'
    fig.savefig(fname)

    # plt.show()
    plt.close()


def plot_electric_field(pic_info, ct, run_name, shock_pos, base_dir='../../'):
    """Plot electric field

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        ct current time frame.
    """
    xmin, xmax = 0, pic_info.lx_di
    xmax = 105
    zmin, zmax = -0.5*pic_info.lz_di, 0.5*pic_info.lz_di
    kwargs = {"current_time":ct, "xl":xmin, "xr":xmax, "zb":zmin, "zt":zmax}
    fname = base_dir + 'data1/ex.gda'
    x, z, efield = read_2d_fields(pic_info, fname, **kwargs) 
    fname = base_dir + 'data1/Ay.gda'
    x, z, Ay = read_2d_fields(pic_info, fname, **kwargs) 
    nx, = x.shape
    nz, = z.shape
    xm = x[shock_pos]

    w1, h1 = 0.85, 0.85
    xs, ys = 0.1, 0.95 - h1
    gap = 0.05

    width, height = 14, 10
    fig = plt.figure(figsize=[width, height])
    ax1 = fig.add_axes([xs, ys, w1, h1])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-0.2, "vmax":0.2}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, efield, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    nlevels = 15
    levels = np.linspace(np.min(Ay), np.max(Ay), nlevels)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5, levels=levels)
    ax1.plot([xm, xm], [z[0], z[-1]], color='black', linestyle='--', linewidth=2)
    ax1.set_xlim([xmin, xmax])
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    # lname = r'$n_' + species + '$'
    # cbar1.ax.set_ylabel(lname, fontdict=font, fontsize=24)
    # cbar1.ax.tick_params(labelsize=24)

    fig_dir = '../img/img_number_densities/' + run_name + '/'
    mkdir_p(fig_dir)
    # fname = fig_dir + '/nrho_linear_' + species + '_' + str(ct).zfill(3) + '.jpg'
    # fig.savefig(fname)

    plt.show()
    # plt.close()


def get_anisotropy_data(pic_info, species, ct, rootpath='../../'):
    """
    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        ct: current time frame.
        rootpath: the root path of a run.
    """
    kwargs = {"current_time":ct, "xl":0, "xr":200, "zb":-20, "zt":20}
    fname = rootpath + 'data/p' + species + '-xx.gda'
    x, z, pxx = read_2d_fields(pic_info, fname, **kwargs) 
    fname = rootpath + 'data/p' + species + '-yy.gda'
    x, z, pyy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = rootpath + 'data/p' + species + '-zz.gda'
    x, z, pzz = read_2d_fields(pic_info, fname, **kwargs) 
    fname = rootpath + 'data/p' + species + '-xy.gda'
    x, z, pxy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = rootpath + 'data/p' + species + '-xz.gda'
    x, z, pxz = read_2d_fields(pic_info, fname, **kwargs) 
    fname = rootpath + 'data/p' + species + '-yz.gda'
    x, z, pyz = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, bx = read_2d_fields(pic_info, rootpath + "data/bx.gda", **kwargs) 
    x, z, by = read_2d_fields(pic_info, rootpath + "data/by.gda", **kwargs) 
    x, z, bz = read_2d_fields(pic_info, rootpath + "data/bz.gda", **kwargs) 
    x, z, absB = read_2d_fields(pic_info, rootpath + "data/absB.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, rootpath + "data/Ay.gda", **kwargs) 
    ppara = pxx*bx*bx + pyy*by*by + pzz*bz*bz + \
            pxy*bx*by*2.0 + pxz*bx*bz*2.0 + pyz*by*bz*2.0
    ppara /= absB * absB
    pperp = 0.5 * (pxx+pyy+pzz-ppara)
    return (ppara, pperp, Ay, x, z)


def plot_anisotropy(pic_info, ct):
    """Plot pressure anisotropy.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        ct: current time frame.
    """
    ppara_e, pperp_e, Ay, x, z = get_anisotropy_data(pic_info, 'e', ct)
    ppara_i, pperp_i, Ay, x, z = get_anisotropy_data(pic_info, 'i', ct)
    nx, = x.shape
    nz, = z.shape
    width = 0.8
    height = 0.37
    xs = 0.12
    ys = 0.92 - height
    gap = 0.05

    fig = plt.figure(figsize=[7,5])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "is_log":True, "vmin":0.1, "vmax":10}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, ppara_e/pperp_e, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.tick_params(axis='x', labelbottom='off')
    ax1.text(0.1, 0.9, r'$p_{e\parallel}/p_{e\perp}$', color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    p2, cbar2 = plot_2d_contour(x, z, ppara_i/pperp_i, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.seismic)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax2.text(0.1, 0.9, r'$p_{i\parallel}/p_{i\perp}$', color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)

    t_wci = ct * pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=20)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    dir = '../img/anisotropy/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    fname = dir + 'anisotropy_' + str(ct).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=200)
    plt.close()

    # plt.show()


def plot_anisotropy_multi(species):
    """Plot pressure anisotropy for multiple runs.

    Args:
        species: 'e' for electrons, 'i' for ions.
    """
    width = 0.8
    height = 0.1
    xs = 0.12
    ys = 0.92 - height
    gap = 0.02
    fig = plt.figure(figsize=[7,12])

    ct = 20
    base_dirs, run_names = ApJ_long_paper_runs()
    for base_dir, run_name in zip(base_dirs, run_names):
        picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
        pic_info = read_data_from_json(picinfo_fname)
        ppara, pperp, Ay, x, z = \
                get_anisotropy_data(pic_info, species, ct, base_dir)
        nx, = x.shape
        nz, = z.shape
        ax1 = fig.add_axes([xs, ys, width, height])
        kwargs_plot = {"xstep":2, "zstep":2, "is_log":True, "vmin":0.1, "vmax":10}
        xstep = kwargs_plot["xstep"]
        zstep = kwargs_plot["zstep"]
        p1, cbar1 = plot_2d_contour(x, z, ppara/pperp, ax1, fig, **kwargs_plot)
        p1.set_cmap(plt.cm.seismic)
        ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
                colors='black', linewidths=0.5)
        ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
        ys -= height + gap

    plt.show()


def plot_beta_rho(pic_info):
    """Plot plasma beta and number density.

    Args:
        pic_info: namedtuple for the PIC simulation information.
    """
    kwargs = {"current_time":20, "xl":0, "xr":200, "zb":-10, "zt":10}
    x, z, pexx = read_2d_fields(pic_info, "../../data/pe-xx.gda", **kwargs) 
    x, z, peyy = read_2d_fields(pic_info, "../../data/pe-yy.gda", **kwargs) 
    x, z, pezz = read_2d_fields(pic_info, "../../data/pe-zz.gda", **kwargs) 
    x, z, absB = read_2d_fields(pic_info, "../../data/absB.gda", **kwargs) 
    x, z, eEB05 = read_2d_fields(pic_info, "../../data/eEB05.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    beta_e = (pexx+peyy+pezz)*2/(3*absB**2)
    width = 0.8
    height = 0.3
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[7,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "is_log":True, "vmin":0.01, "vmax":10}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, beta_e, ax1, fig, **kwargs_plot)
    p1.set_cmap(cmaps.plasma)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='white', linewidths=0.5)
    ax1.tick_params(axis='x', labelbottom='off')
    ax1.set_title(r'$\beta_e$', fontsize=24)

    ys -= height + 0.15
    ax2 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2}
    p2, cbar2 = plot_2d_contour(x, z, eEB05, ax2, fig, **kwargs_plot)
    # p2.set_cmap(cmaps.magma)
    # p2.set_cmap(cmaps.inferno)
    p2.set_cmap(cmaps.plasma)
    # p2.set_cmap(cmaps.viridis)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='white', linewidths=0.5)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax2.set_title(r'$n_{acc}/n_e$', fontsize=24)
    cbar2.set_ticks(np.arange(0.2, 1.0, 0.2))
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    fig.savefig('../img/beta_e_ne_2.eps')
    plt.show()

def plot_jdote_2d(pic_info):
    """Plot jdotE due to drift current.
    Args:
        pic_info: namedtuple for the PIC simulation information.
    """
    kwargs = {"current_time":40, "xl":0, "xr":200, "zb":-10, "zt":10}
    x, z, jcpara_dote = read_2d_fields(pic_info, 
            "../data1/jcpara_dote00_e.gda", **kwargs) 
    x, z, jgrad_dote = read_2d_fields(pic_info, 
            "../data1/jgrad_dote00_e.gda", **kwargs) 
    x, z, agyp = read_2d_fields(pic_info, 
            "../data1/agyrotropy00_e.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../data/Ay.gda", **kwargs) 
    jdote_norm = 1E3
    jcpara_dote *= jdote_norm
    jgrad_dote *= jdote_norm
    nx, = x.shape
    nz, = z.shape
    width = 0.78
    height = 0.25
    xs = 0.14
    xe = 0.94 - xs
    ys = 0.96 - height
    fig = plt.figure(figsize=(7,5))
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-1, "vmax":1}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, jcpara_dote, ax1, fig, **kwargs_plot)
    p1.set_cmap(cmaps.viridis)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    cbar1.set_ticks(np.arange(-0.8, 1.0, 0.4))
    ax1.tick_params(axis='x', labelbottom='off')
    ax1.text(5, 5.2, r'$\mathbf{j}_c\cdot\mathbf{E}$', color='blue', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0))
    
    ys -= height + 0.035
    ax2 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-1, "vmax":1}
    p2, cbar2 = plot_2d_contour(x, z, jcpara_dote, ax2, fig, **kwargs_plot)
    p2.set_cmap(cmaps.viridis)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    cbar2.set_ticks(np.arange(-0.8, 1.0, 0.4))
    ax2.tick_params(axis='x', labelbottom='off')
    ax2.text(5, 5, r'$\mathbf{j}_g\cdot\mathbf{E}$', color='green', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0))

    ys -= height + 0.035
    ax3 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":0, "vmax":1.5}
    p3, cbar3 = plot_2d_contour(x, z, agyp, ax3, fig, **kwargs_plot)
    p3.set_cmap(cmaps.viridis)
    ax3.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    cbar3.set_ticks(np.arange(0, 1.6, 0.4))
    ax3.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax3.text(5, 5, r'$A_e$', color='black', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0))

    plt.show()

def plot_phi_parallel(ct, pic_info):
    """Plot parallel potential.
    Args:
        ct: current time frame.
        pic_info: namedtuple for the PIC simulation information.
    """
    kwargs = {"current_time":ct, "xl":0, "xr":200, "zb":-20, "zt":20}
    x, z, phi_para = read_2d_fields(pic_info, 
            "../../data1/phi_para.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 

    # phi_para_new = phi_para
    nk = 7
    phi_para_new = signal.medfilt2d(phi_para, kernel_size=(nk, nk))
    # phi_para_new = signal.wiener(phi_para, mysize=5)
    # ng = 9
    # kernel = np.ones((ng,ng)) / float(ng*ng)
    # phi_para_new = signal.convolve2d(phi_para, kernel)

    # fft_transform = np.fft.fft2(phi_para)
    # power_spectrum = np.abs(fft_transform)**2
    # scaled_power_spectrum = np.log10(power_spectrum)
    # scaled_ps0 = scaled_power_spectrum - np.max(scaled_power_spectrum)
    # # print np.min(scaled_ps0), np.max(scaled_ps0)

    # freqx = np.fft.fftfreq(x.size)
    # freqz = np.fft.fftfreq(z.size)
    # xv, zv = np.meshgrid(freqx, freqz)
    # #print np.max(freqx), np.min(freqx)
    # #m = np.ma.masked_where(scaled_ps0 > -8.8, scaled_ps0)
    # #new_fft_spectrum = np.ma.masked_array(fft_transform, m.mask)
    # new_fft_spectrum = fft_transform.copy()
    # #new_fft_spectrum[scaled_ps0 < -1.3] = 0.0
    # print np.max(xv), np.min(xv)
    # new_fft_spectrum[xv > 0.02] = 0.0
    # new_fft_spectrum[xv < -0.02] = 0.0
    # new_fft_spectrum[zv > 0.02] = 0.0
    # new_fft_spectrum[zv < -0.02] = 0.0

    # data = np.fft.ifft2(new_fft_spectrum)

    nx, = x.shape
    nz, = z.shape
    width = 0.85
    height = 0.85
    xs = 0.1
    xe = 0.95 - xs
    ys = 0.96 - height
    fig = plt.figure(figsize=(10, 5))
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.05, "vmax":0.05}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    im1, cbar1 = plot_2d_contour(x, z, phi_para_new, ax1, fig, **kwargs_plot)
    #im1 = plt.imshow(data.real, vmin=-0.1, vmax=0.1)
    im1.set_cmap(plt.cm.seismic)
    
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5, 
            levels=np.arange(np.min(Ay), np.max(Ay), 15))
    # cbar1.set_ticks(np.arange(-0.2, 0.2, 0.05))
    #ax1.tick_params(axis='x', labelbottom='off')
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax1.set_ylabel(r'$y/d_i$', fontdict=font, fontsize=20)
    
    #plt.close()
    plt.show()

def plot_Ey(pic_info, species, current_time):
    """Plot out-of-plane current density.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-50, "zt":50}
    x, z, ey = read_2d_fields(pic_info, "../../data/ey.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.1, "vmax":0.1}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, ey, ax1, fig, **kwargs_plot)
    p1.set_cmap(cmaps.plasma)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    cbar1.ax.set_ylabel(r'$E_y$', fontdict=font, fontsize=24)
    cbar1.set_ticks(np.arange(-0.08, 0.1, 0.04))
    cbar1.ax.tick_params(labelsize=24)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir('../img/img_ey/'):
        os.makedirs('../img/img_ey/')
    fname = '../img/img_ey/ey_' + str(current_time).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=200)

    plt.show()
    # plt.close()

def plot_jy_Ey(pic_info, species, current_time):
    """Plot out-of-plane current density.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-50, "zt":50}
    x, z, ey = read_2d_fields(pic_info, "../data/ey.gda", **kwargs) 
    x, z, jy = read_2d_fields(pic_info, "../data/jy.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.01, "vmax":0.01}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, jy*ey, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    cbar1.ax.set_ylabel(r'$j_yE_y$', fontdict=font, fontsize=24)
    cbar1.set_ticks(np.arange(-0.01, 0.015, 0.01))
    cbar1.ax.tick_params(labelsize=24)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir('../img/img_jy_ey/'):
        os.makedirs('../img/img_jy_ey/')
    fname = '../img/img_jy_ey/jy_ey' + '_' + str(current_time).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=200)

    #plt.show()
    plt.close()

def plot_jpolar_dote(pic_info, species, current_time):
    """Plot out-of-plane current density.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":400, "zb":-100, "zt":100}
    x, z, jpolar_dote = read_2d_fields(pic_info, "../../data1/jpolar_dote00_e.gda", **kwargs) 
    # x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-1, "vmax":1}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, jpolar_dote, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    # ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
    #         colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    # cbar1.ax.set_ylabel(r'$j_yE_y$', fontdict=font, fontsize=24)
    # cbar1.set_ticks(np.arange(-0.01, 0.015, 0.01))
    cbar1.ax.tick_params(labelsize=24)
    plt.show()

def plot_epara(pic_info, species, current_time):
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-10, "zt":10}
    x, z, bx = read_2d_fields(pic_info, "../../data/bx.gda", **kwargs) 
    x, z, by = read_2d_fields(pic_info, "../../data/by.gda", **kwargs) 
    x, z, bz = read_2d_fields(pic_info, "../../data/bz.gda", **kwargs) 
    x, z, absB = read_2d_fields(pic_info, "../../data/absB.gda", **kwargs) 
    x, z, ex = read_2d_fields(pic_info, "../../data/ex.gda", **kwargs) 
    x, z, ey = read_2d_fields(pic_info, "../../data/ey.gda", **kwargs) 
    x, z, ez = read_2d_fields(pic_info, "../../data/ez.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 

    absE = np.sqrt(ex*ex + ey*ey + ez*ez)
    epara = (ex*bx + ey*by + ez*bz) / absB
    eperp = np.sqrt(absE*absE - epara*epara)
    ng = 3
    kernel = np.ones((ng,ng)) / float(ng*ng)
    epara = signal.convolve2d(epara, kernel)
    eperp = signal.convolve2d(eperp, kernel)

    nx, = x.shape
    nz, = z.shape
    width = 0.79
    height = 0.37
    xs = 0.12
    ys = 0.92 - height
    gap = 0.05

    fig = plt.figure(figsize=[7, 5])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":0, "vmax":0.1}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, eperp, ax1, fig, **kwargs_plot)
    # p1.set_cmap(cmaps.inferno)
    p1.set_cmap(plt.cm.get_cmap('hot'))
    Ay_min = np.min(Ay)
    Ay_max = np.max(Ay)
    levels = np.linspace(Ay_min, Ay_max, 10)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='white', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    # ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(axis='x', labelbottom='off')
    ax1.tick_params(labelsize=16)
    # cbar1.ax.set_ylabel(r'$E_\perp$', fontdict=font, fontsize=20)
    cbar1.set_ticks(np.arange(0, 0.1, 0.03))
    cbar1.ax.tick_params(labelsize=16)
    ax1.text(0.02, 0.8, r'$E_\perp$', color='w', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.05, "vmax":0.05}
    p2, cbar2 = plot_2d_contour(x, z, epara, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.seismic)
    # p2.set_cmap(cmaps.plasma)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax2.tick_params(labelsize=16)
    # cbar2.ax.set_ylabel(r'$E_\parallel$', fontdict=font, fontsize=24)
    cbar2.set_ticks(np.arange(-0.04, 0.05, 0.02))
    cbar2.ax.tick_params(labelsize=16)
    ax2.text(0.02, 0.8, r'$E_\parallel$', color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)

    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=20)
    
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    dir = '../img/img_epara/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    # fname = dir + 'epara_perp' + '_' + str(current_time).zfill(3) + '.jpg'
    # fig.savefig(fname, dpi=200)
    fname = dir + 'epara_perp' + '_' + str(current_time).zfill(3) + '.eps'
    fig.savefig(fname)

    plt.show()
    # plt.close()


def plot_diff_fields(pic_info, species, current_time):
    """Plot the differential of the fields.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-20, "zt":20}
    x, z, data = read_2d_fields(pic_info, "../../data/absB.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.01, "vmax":0.01}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    data_new = np.zeros((nz, nx))
    # data_new[:, 0:nx-1] = data[:, 1:nx] - data[:, 0:nx-1]
    data_new[0:nz-1, :] = data[1:nz, :] - data[0:nz-1, :]
    ng = 5
    kernel = np.ones((ng,ng)) / float(ng*ng)
    data_new = signal.convolve2d(data_new, kernel)
    p1, cbar1 = plot_2d_contour(x, z, data_new, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    # p1.set_cmap(cmaps.inferno)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    cbar1.ax.set_ylabel(r'$j_y$', fontdict=font, fontsize=24)
    cbar1.set_ticks(np.arange(-0.4, 0.5, 0.2))
    cbar1.ax.tick_params(labelsize=24)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    plt.show()


def plot_jpara_perp(pic_info, species, current_time):
    """Plot the energy conversion from parallel and perpendicular direction.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-20, "zt":20}
    x, z, data = read_2d_fields(pic_info, "../../data1/jqnvperp_dote00_e.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    dmax = -0.0005
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-dmax, "vmax":dmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    data_new = np.zeros((nz, nx))
    ng = 5
    kernel = np.ones((ng,ng)) / float(ng*ng)
    data_new = signal.convolve2d(data, kernel)
    p1, cbar1 = plot_2d_contour(x, z, data_new, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    # p1.set_cmap(cmaps.inferno)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    # cbar1.ax.set_ylabel(r'$j_y$', fontdict=font, fontsize=24)
    # cbar1.set_ticks(np.arange(-0.4, 0.5, 0.2))
    cbar1.ax.tick_params(labelsize=24)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    plt.show()


def plot_ux(pic_info, species, current_time):
    """Plot the in-plane bulk velocity field.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-50, "zt":50}
    fname = "../../data/vex.gda"
    if not os.path.isfile(fname):
        fname = "../../data/uex.gda"
    x, z, uex = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, ne = read_2d_fields(pic_info, "../../data/ne.gda", **kwargs) 
    fname = "../../data/vix.gda"
    if not os.path.isfile(fname):
        fname = "../../data/uix.gda"
    x, z, uix = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, ni = read_2d_fields(pic_info, "../../data/ni.gda", **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    wpe_wce = pic_info.dtwce / pic_info.dtwpe
    va = wpe_wce / math.sqrt(pic_info.mime)  # Alfven speed of inflow region
    ux = (uex*ne + uix*ni*pic_info.mime) / (ne + ni*pic_info.mime)
    ux /= va
    nx, = x.shape
    nz, = z.shape
    width = 0.79
    height = 0.37
    xs = 0.13
    ys = 0.92 - height
    gap = 0.05
    # width = 0.75
    # height = 0.4
    # xs = 0.15
    # ys = 0.92 - height
    fig = plt.figure(figsize=[7,5])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-1.0, "vmax":1.0}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, ux, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    # p1.set_cmap(cmaps.inferno)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax1.tick_params(axis='x', labelbottom='off')
    ax1.tick_params(labelsize=16)
    cbar1.set_ticks(np.arange(-0.8, 1.0, 0.4))
    cbar1.ax.tick_params(labelsize=16)
    ax1.text(0.02, 0.8, r'$u_x/V_A$', color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)
    ax1.plot([np.min(x), np.max(x)], [0, 0], linestyle='--', color='k', linewidth=2)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=20)

    gap = 0.06
    ys0 = 0.15
    height0 = ys - gap - ys0
    w1, h1 = fig.get_size_inches()
    width0 = width * 0.98 - 0.05 / w1
    ax2 = fig.add_axes([xs, ys0, width0, height0])
    ax2.plot(x, ux[nz/2, :], color='k', linewidth=1)
    ax2.plot([np.min(x), np.max(x)], [0, 0], linestyle='--', color='k')
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax2.set_ylabel(r'$u_x/V_A$', fontdict=font, fontsize=20)
    ax2.tick_params(labelsize=16)
    ax2.set_ylim([-1, 1])

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    dir = '../img/velocity/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    fname = dir + 'vx_' + str(current_time) + '.eps'
    fig.savefig(fname)

    plt.show()
    # plt.close()

def plot_uy(pic_info, current_time):
    """Plot the out-of-plane bulk velocity field.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-50, "zt":50}
    fname = "../../data/vey.gda"
    if not os.path.isfile(fname):
        fname = "../../data/uey.gda"
    x, z, uey = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/viy.gda"
    if not os.path.isfile(fname):
        fname = "../../data/uiy.gda"
    x, z, uiy = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    wpe_wce = pic_info.dtwce / pic_info.dtwpe
    va = wpe_wce / math.sqrt(pic_info.mime)  # Alfven speed of inflow region
    uey /= va
    uiy /= va
    nx, = x.shape
    nz, = z.shape
    width = 0.79
    height = 0.37
    xs = 0.13
    ys = 0.92 - height
    gap = 0.05
    fig = plt.figure(figsize=[7,5])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":2, "zstep":2, "vmin":-0.5, "vmax":0.5}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, uey, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    # p1.set_cmap(cmaps.inferno)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax1.tick_params(axis='x', labelbottom='off')
    ax1.tick_params(labelsize=16)
    cbar1.set_ticks(np.arange(-0.4, 0.5, 0.2))
    cbar1.ax.tick_params(labelsize=16)
    ax1.text(0.02, 0.8, r'$u_{ey}/V_A$', color='k', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.5, "vmax":0.5}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p2, cbar2 = plot_2d_contour(x, z, uiy, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.get_cmap('seismic'))
    # p1.set_cmap(cmaps.inferno)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=20)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=20)
    ax2.tick_params(labelsize=16)
    cbar2.set_ticks(np.arange(-0.4, 0.5, 0.2))
    cbar2.ax.tick_params(labelsize=16)
    ax2.text(0.02, 0.8, r'$u_{iy}/V_A$', color='k', fontsize=20,
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=20)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    dir = '../img/velocity/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    fname = dir + 'vy_' + str(current_time) + '.eps'
    fig.savefig(fname)

    plt.show()
    # plt.close()


def locate_shock(pic_info, ct, run_name, base_dir='../../'):
    """Locate the location of shocks

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        ct current time frame.
    """
    xmin, xmax = 0, pic_info.lx_di
    xmax = 105
    zmin, zmax = -0.5*pic_info.lz_di, 0.5*pic_info.lz_di
    kwargs = {"current_time":ct, "xl":xmin, "xr":xmax, "zb":zmin, "zt":zmax}
    fname = base_dir + 'data1/ne.gda'
    x, z, ne = read_2d_fields(pic_info, fname, **kwargs) 
    fname = base_dir + 'data1/ni.gda'
    x, z, ni = read_2d_fields(pic_info, fname, **kwargs) 
    fname = base_dir + 'data1/vex.gda'
    x, z, vex = read_2d_fields(pic_info, fname, **kwargs) 
    fname = base_dir + 'data1/vix.gda'
    x, z, vix = read_2d_fields(pic_info, fname, **kwargs) 
    fname = base_dir + 'data1/Ay.gda'
    x, z, Ay = read_2d_fields(pic_info, fname, **kwargs) 
    nx, = x.shape
    nz, = z.shape
    xs = 0
    ne_cum = np.sum(ne, axis=0) / nz
    ne_grad = np.abs(np.gradient(ne_cum))
    max_index1 = np.argmax(ne_grad[xs:])
    ni_cum = np.sum(ni, axis=0) / nz
    ni_grad = np.abs(np.gradient(ni_cum))
    max_index2 = np.argmax(ni_grad[xs:])
    vex_cum = np.sum(vex, axis=0) / nz
    vex_grad = np.abs(np.gradient(vex_cum))
    max_index3 = np.argmax(vex_grad[xs:])
    vix_cum = np.sum(vix, axis=0) / nz
    vix_grad = np.abs(np.gradient(vix_cum))
    max_index4 = np.argmax(vix_grad[xs:])
    max_indices = [max_index1, max_index2, max_index3, max_index4]
    fdir = '../data/shock_pos/'
    mkdir_p(fdir)
    fname = fdir + 'shock_pos_' + str(ct) + '.txt'
    np.savetxt(fname, [max(max_indices)])


def combine_shock_files(ntf):
    """Combine all shock location files at different time frame

    The shock position is saved in different file because Parallel
    in joblib cannot shock one global array
    
    """
    fdir = '../data/shock_pos/'
    shock_loc = np.zeros(ntf - 1)
    for ct in range(ntf - 1):
        print ct
        fname = fdir + 'shock_pos_' + str(ct) + '.txt'
        shock_loc[ct] = np.genfromtxt(fname)
    shock_loc[0] = 0
    # plt.plot(shock_loc)
    # plt.show()
    fname = fdir + 'shock_pos.txt'
    np.savetxt(fname, shock_loc, fmt='%d')


if __name__ == "__main__":
    # pic_info = pic_information.get_pic_info('../../')
    # ntp = pic_info.ntp
    # plot_beta_rho(pic_info)
    # plot_jdote_2d(pic_info)
    # plot_anistropy(pic_info, 'e')
    # plot_phi_parallel(29, pic_info)
    # maps = sorted(m for m in plt.cm.datad if not m.endswith("_r")) # nmaps = len(maps) + 1 # print nmaps
    # for i in range(200):
    #     # plot_number_density(pic_info, 'e', i)
    #     # plot_jy(pic_info, 'e', i)
    #     # plot_Ey(pic_info, 'e', i)
    #     plot_anisotropy(pic_info, i)
    # plot_number_density(pic_info, 'e', 40)
    # plot_jy(pic_info, 'e', 120)
    # for i in range(90, 170, 10):
    #     plot_absB_jy(pic_info, 'e', i)
    # plot_by(pic_info)
    # plot_by_multi()
    # plot_ux(pic_info, 'e', 160)
    # plot_uy(pic_info, 160)
    # plot_diff_fields(pic_info, 'e', 120)
    # plot_jpara_perp(pic_info, 'e', 120)
    # plot_Ey(pic_info, 'e', 40)
    # plot_jy_Ey(pic_info, 'e', 40)
    # for i in range(pic_info.ntf):
    #     plot_Ey(pic_info, 'e', i)

    # for i in range(pic_info.ntf):
    #     plot_jy_Ey(pic_info, 'e', i)
    # plot_jpolar_dote(pic_info, 'e', 30)
    # plot_epara(pic_info, 'e', 35)
    # plot_anisotropy_multi('e')
    base_dir = '/net/scratch3/xiaocanli/2D-90-Mach4-sheet4-multi/'
    run_name = '2D-90-Mach4-sheet4-multi'
    picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
    pic_info = read_data_from_json(picinfo_fname)
    ntf = pic_info.ntf
    # combine_shock_files(ntf)
    # ct = ntf - 2
    ct = 302
    cts = range(ntf - 1)
    shock_loc = np.genfromtxt('../data/shock_pos/shock_pos.txt', dtype=np.int32)
    def processInput(ct):
        print ct
        plot_number_density(pic_info, 'i', ct, run_name, shock_loc[ct], base_dir)
        # plot_vx(pic_info, 'i', ct, run_name, shock_loc[ct], base_dir)
        # shock_pos = locate_shock(pic_info, ct, run_name, base_dir)
    num_cores = multiprocessing.cpu_count()
    # Parallel(n_jobs=num_cores)(delayed(processInput)(ct) for ct in cts)
    # plot_number_density(pic_info, 'e', ct, run_name, shock_loc[ct], base_dir)
    # plot_vx(pic_info, 'i', ct, run_name, shock_loc[ct], base_dir)
    plot_electric_field(pic_info, ct, run_name, shock_loc[ct], base_dir)
