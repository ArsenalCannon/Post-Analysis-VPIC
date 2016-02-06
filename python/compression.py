"""
Analysis procedures for compression related terms.
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
from scipy.interpolate import spline
import math
import os.path
import struct
import collections
import pic_information
from contour_plots import read_2d_fields, plot_2d_contour
from energy_conversion import read_jdote_data, read_data_from_json
from runs_name_path import ApJ_long_paper_runs

rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
mpl.rc('text', usetex=True)
mpl.rcParams['text.latex.preamble'] = [r"\usepackage{amsmath}"]

font = {'family' : 'serif',
        #'color'  : 'darkred',
        'color'  : 'black',
        'weight' : 'normal',
        'size'   : 24,
        }

def plot_compression(pic_info, species, current_time):
    """Plot compression related terms.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-50, "zt":50}
    fname = "../../data1/vdot_div_ptensor00_" + species + ".gda"
    x, z, vdot_div_ptensor = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pdiv_u00_" + species + ".gda"
    x, z, pdiv_u = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/div_u00_" + species + ".gda"
    x, z, div_u = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pshear00_" + species + ".gda"
    x, z, pshear = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/div_vdot_ptensor00_" + species + ".gda"
    x, z, div_vdot_ptensor = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    fname = '../../data/u' + species + 'x.gda'
    x, z, ux = read_2d_fields(pic_info, fname, **kwargs) 
    fname = '../../data/u' + species + 'y.gda'
    x, z, uy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = '../../data/u' + species + 'z.gda'
    x, z, uz = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, ex = read_2d_fields(pic_info, '../../data/ex.gda', **kwargs) 
    x, z, ey = read_2d_fields(pic_info, '../../data/ey.gda', **kwargs) 
    x, z, ez = read_2d_fields(pic_info, '../../data/ez.gda', **kwargs) 
    fname = '../../data/n' + species + '.gda'
    x, z, nrho = read_2d_fields(pic_info, fname, **kwargs) 
    if species == 'e':
        jdote = - (ux*ex + uy*ey + uz*ez) * nrho
    else:
        jdote = (ux*ex + uy*ey + uz*ez) * nrho

    pdiv_u_sum = np.sum(pdiv_u, axis=0)
    pdiv_u_cum = np.cumsum(pdiv_u_sum)
    pshear_sum = np.sum(pshear, axis=0)
    pshear_cum = np.cumsum(pshear_sum)
    pcomp1_sum = np.sum(div_vdot_ptensor, axis=0)
    pcomp1_cum = np.cumsum(pcomp1_sum)
    data4 = pdiv_u + pshear + div_vdot_ptensor
    pcomp2_sum = np.sum(data4, axis=0)
    pcomp2_cum = np.cumsum(pcomp2_sum)
    pcomp3_sum = np.sum(vdot_div_ptensor, axis=0)
    pcomp3_cum = np.cumsum(pcomp3_sum)
    jdote_sum = np.sum(jdote, axis=0)
    jdote_cum = np.cumsum(jdote_sum)

    nx, = x.shape
    nz, = z.shape
    zl = nz / 4
    zt = nz - zl
    nk = 5
    div_u_new = signal.medfilt2d(div_u[zl:zt, :], kernel_size=(nk,nk))
    pdiv_u_new = signal.medfilt2d(pdiv_u[zl:zt, :], kernel_size=(nk,nk))
    pshear_new = signal.medfilt2d(pshear[zl:zt, :], kernel_size=(nk,nk))
    vdot_div_ptensor_new = signal.medfilt2d(vdot_div_ptensor[zl:zt, :],
            kernel_size=(nk,nk))
    div_vdot_ptensor_new = signal.medfilt2d(div_vdot_ptensor[zl:zt, :],
            kernel_size=(nk,nk))
    jdote_new = signal.medfilt2d(jdote[zl:zt, :], kernel_size=(nk,nk))
    data4_new = pdiv_u_new + pshear_new + div_vdot_ptensor_new

    width = 0.75
    height = 0.11
    xs = 0.12
    ys = 0.98 - height
    gap = 0.025

    vmin = -0.005
    vmax = 0.005
    fig = plt.figure(figsize=[10,14])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z[zl:zt], pdiv_u_new, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    ax1.contour(x[0:nx:xstep], z[zl:zt:zstep], Ay[zl:zt:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=20)
    ax1.tick_params(axis='x', labelbottom='off')
    cbar1.set_ticks(np.arange(-0.004, 0.005, 0.002))
    cbar1.ax.tick_params(labelsize=20)
    fname1 = r'$-p\nabla\cdot\mathbf{u}$'
    ax1.text(0.02, 0.8, fname1, color='red', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p2, cbar2 = plot_2d_contour(x, z[zl:zt], pshear_new, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.seismic)
    ax2.contour(x[0:nx:xstep], z[zl:zt:zstep], Ay[zl:zt:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax2.tick_params(labelsize=20)
    ax2.tick_params(axis='x', labelbottom='off')
    cbar2.set_ticks(np.arange(-0.004, 0.005, 0.002))
    cbar2.ax.tick_params(labelsize=20)
    fname2 = r'$-(p_\parallel - p_\perp)b_ib_j\sigma_{ij}$'
    ax2.text(0.02, 0.8, fname2, color='green', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)
    
    ys -= height + gap
    ax3 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p3, cbar3 = plot_2d_contour(x, z[zl:zt], div_vdot_ptensor_new, 
            ax3, fig, **kwargs_plot)
    p3.set_cmap(plt.cm.seismic)
    ax3.contour(x[0:nx:xstep], z[zl:zt:zstep], Ay[zl:zt:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax3.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax3.tick_params(labelsize=20)
    ax3.tick_params(axis='x', labelbottom='off')
    cbar3.set_ticks(np.arange(-0.004, 0.005, 0.002))
    cbar3.ax.tick_params(labelsize=20)
    fname3 = r'$\nabla\cdot(\mathbf{u}\cdot\mathcal{P})$'
    ax3.text(0.02, 0.8, fname3, color='blue', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax3.transAxes)

    ys -= height + gap
    ax4 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p4, cbar4 = plot_2d_contour(x, z[zl:zt], data4_new, ax4, fig, **kwargs_plot)
    p4.set_cmap(plt.cm.seismic)
    ax4.contour(x[0:nx:xstep], z[zl:zt:zstep], Ay[zl:zt:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax4.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax4.tick_params(labelsize=20)
    ax4.tick_params(axis='x', labelbottom='off')
    cbar4.set_ticks(np.arange(-0.004, 0.005, 0.002))
    cbar4.ax.tick_params(labelsize=20)
    fname4 = fname3 + fname1 + fname2
    ax4.text(0.02, 0.8, fname4, color='darkred', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax4.transAxes)

    ys -= height + gap
    ax5 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p5, cbar5 = plot_2d_contour(x, z[zl:zt], vdot_div_ptensor_new,
            ax5, fig, **kwargs_plot)
    p5.set_cmap(plt.cm.seismic)
    ax5.contour(x[0:nx:xstep], z[zl:zt:zstep], Ay[zl:zt:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax5.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax5.tick_params(labelsize=20)
    ax5.tick_params(axis='x', labelbottom='off')
    cbar5.set_ticks(np.arange(-0.004, 0.005, 0.002))
    cbar5.ax.tick_params(labelsize=20)
    ax5.text(0.02, 0.8, r'$\mathbf{u}\cdot(\nabla\cdot\mathcal{P})$',
            color='black', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax5.transAxes)

    ys -= height + gap
    ax6 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p6, cbar6 = plot_2d_contour(x, z[zl:zt], jdote_new, ax6, fig, **kwargs_plot)
    p6.set_cmap(plt.cm.seismic)
    ax6.contour(x[0:nx:xstep], z[zl:zt:zstep], Ay[zl:zt:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax6.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax6.tick_params(labelsize=20)
    ax6.tick_params(axis='x', labelbottom='off')
    cbar6.set_ticks(np.arange(-0.004, 0.005, 0.002))
    cbar6.ax.tick_params(labelsize=20)
    fname6 = r'$' + '\mathbf{j}_' + species + '\cdot\mathbf{E}' + '$'
    ax6.text(0.02, 0.8, fname6, color='black', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax6.transAxes)

    ys -= height + gap
    w1, h1 = fig.get_size_inches()
    width1 = width * 0.98 - 0.05 / w1
    ax7 = fig.add_axes([xs, ys, width1, height])
    ax7.plot(x, pdiv_u_sum, linewidth=2, color='r')
    ax7.plot(x, pshear_sum, linewidth=2, color='g')
    ax7.plot(x, pcomp1_sum, linewidth=2, color='b')
    ax7.plot(x, pcomp2_sum, linewidth=2, color='darkred')
    ax7.plot(x, pcomp3_sum, linewidth=2, color='k')
    ax7.plot(x, jdote_sum, linewidth=2, color='k', linestyle='-.')
    xmax = np.max(x)
    xmin = np.min(x)
    # ax7.set_ylim([-0.2, 0.2])
    ax7.plot([xmin, xmax], [0, 0], color='k', linestyle='--')
    ax7.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax7.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax7.tick_params(labelsize=20)

    # width = 0.75
    # height = 0.73
    # xs = 0.12
    # ys = 0.96 - height
    # fig = plt.figure(figsize=[10,3])
    # ax1 = fig.add_axes([xs, ys, width, height])
    # kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.1, "vmax":0.1}
    # xstep = kwargs_plot["xstep"]
    # zstep = kwargs_plot["zstep"]
    # p1, cbar1 = plot_2d_contour(x, z, div_u, ax1, fig, **kwargs_plot)
    # p1.set_cmap(plt.cm.seismic)
    # ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
    #         colors='black', linewidths=0.5)
    # ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    # ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    # ax1.tick_params(labelsize=20)
    # cbar1.ax.tick_params(labelsize=20)
    
    plt.show()
    # if not os.path.isdir('../img/'):
    #     os.makedirs('../img/')
    # if not os.path.isdir('../img/img_compression/'):
    #     os.makedirs('../img/img_compression/')
    # fname = 'compression' + str(current_time).zfill(3) + '_' + species + '.jpg'
    # fname = '../img/img_compression/' + fname
    # fig.savefig(fname)
    # plt.close()


def plot_compression_cut(pic_info, species, current_time):
    """Plot compression related terms.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    zmin, zmax = -15, 15
    xmin = xmax = 140
    kwargs = {"current_time":current_time, "xl":xmin, "xr":xmax, "zb":zmin, "zt":zmax}
    fname = "../../data1/vdot_div_ptensor00_" + species + ".gda"
    x, z, vdot_div_ptensor = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pdiv_u00_" + species + ".gda"
    x, z, pdiv_u = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/div_u00_" + species + ".gda"
    x, z, div_u = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pshear00_" + species + ".gda"
    x, z, pshear = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/div_vdot_ptensor00_" + species + ".gda"
    x, z, div_vdot_ptensor = read_2d_fields(pic_info, fname, **kwargs) 
    fname = '../../data/u' + species + 'x.gda'
    x, z, ux = read_2d_fields(pic_info, fname, **kwargs) 
    fname = '../../data/u' + species + 'y.gda'
    x, z, uy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = '../../data/u' + species + 'z.gda'
    x, z, uz = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, ex = read_2d_fields(pic_info, '../../data/ex.gda', **kwargs) 
    x, z, ey = read_2d_fields(pic_info, '../../data/ey.gda', **kwargs) 
    x, z, ez = read_2d_fields(pic_info, '../../data/ez.gda', **kwargs) 
    fname = '../../data/n' + species + '.gda'
    x, z, nrho = read_2d_fields(pic_info, fname, **kwargs) 
    nx, = x.shape
    nz, = z.shape
    if species == 'e':
        je = - (ux*ex + uy*ey + uz*ez) * nrho
    else:
        je = (ux*ex + uy*ey + uz*ez) * nrho

    pdiv_u_cum = np.cumsum(pdiv_u[:, 0])
    pshear_cum = np.cumsum(pshear[:, 0])
    vdot_div_ptensor_cum = np.cumsum(vdot_div_ptensor[:, 0])
    div_vdot_ptensor_cum = np.cumsum(div_vdot_ptensor[:, 0])
    je_cum = np.cumsum(je[:, 0])

    znew = np.linspace(zmin, zmax, nz*10)
    pdiv_u_new = spline(z, pdiv_u[:, 0], znew)
    pshear_new = spline(z, pshear[:, 0], znew)
    div_vdot_ptensor_new = spline(z, div_vdot_ptensor[:, 0], znew)
    vdot_div_ptensor_new = spline(z, vdot_div_ptensor[:, 0], znew)
    je_new = spline(z, je[:, 0], znew)

    pdiv_u_new = spline(z, pdiv_u_cum, znew)
    pshear_new = spline(z, pshear_cum, znew)
    div_vdot_ptensor_new = spline(z, div_vdot_ptensor_cum, znew)
    vdot_div_ptensor_new = spline(z, vdot_div_ptensor_cum, znew)
    je_new = spline(z, je_cum, znew)

    width = 0.88
    height = 0.8
    xs = 0.08
    ys = 0.96 - height

    fig = plt.figure(figsize=[14, 5])
    ax1 = fig.add_axes([xs, ys, width, height])
    label1 = r'$-p\nabla\cdot\mathbf{u}$'
    label2 = r'$-(p_\parallel - p_\perp)b_ib_j\sigma_{ij}$'
    label3 = r'$\nabla\cdot(\mathbf{u}\cdot\mathcal{P})$'
    label4 = label3 + label1 + label2
    label5 = r'$\mathbf{u}\cdot(\nabla\cdot\mathcal{P})$'
    label6 = r'$\mathbf{j}\cdot\mathbf{E}$'
    # signal.medfilt(pdiv_u[:, 0], kernel_size=5)
    # p1 = ax1.plot(znew, pdiv_u_new, linewidth=2, color='r', label=label1)
    # p2 = ax1.plot(znew, pshear_new, linewidth=2, color='g', label=label2)
    # p3 = ax1.plot(znew, div_vdot_ptensor_new, linewidth=2,
    #         color='b', label=label3)
    p4 = ax1.plot(znew, pdiv_u_new + pshear_new + div_vdot_ptensor_new,
            linewidth=2, color='r', label=label4)
    p5 = ax1.plot(znew, vdot_div_ptensor_new, linewidth=2,
            color='g', label=label5)
    p6 = ax1.plot(znew, je_new, linewidth=2, color='b',
            linestyle='-', label=label6)
    ax1.set_xlabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlim([zmin, zmax])
    ax1.tick_params(labelsize=20)
    ax1.legend(loc=2, prop={'size':20}, ncol=1,
            shadow=False, fancybox=False, frameon=False)
    plt.show()
    # if not os.path.isdir('../img/'):
    #     os.makedirs('../img/')
    # if not os.path.isdir('../img/img_compression/'):
    #     os.makedirs('../img/img_compression/')
    # fname = 'compression' + str(current_time).zfill(3) + '_' + species + '.jpg'
    # fname = '../img/img_compression/' + fname
    # fig.savefig(fname)
    # plt.close()


def angle_current(pic_info, current_time):
    """Angle between calculated current and simulation current.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        current_time: current time frame.
    """
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-15, "zt":15}
    fname = "../../data/jx.gda"
    x, z, jx = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/jy.gda"
    x, z, jy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/jz.gda"
    x, z, jz = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/uex.gda"
    x, z, uex = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/uey.gda"
    x, z, uey = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/uez.gda"
    x, z, uez = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/uix.gda"
    x, z, uix = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/uiy.gda"
    x, z, uiy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/uiz.gda"
    x, z, uiz = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/ne.gda"
    x, z, ne = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/ni.gda"
    x, z, ni = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 

    mime = pic_info.mime
    jx1 = -uex * ne + uix * ni
    jy1 = -uey * ne + uiy * ni
    jz1 = -uez * ne + uiz * ni
    absJ = np.sqrt(jx**2 + jy**2 + jz**2)
    absJ1 = np.sqrt(jx1**2 + jy1**2 + jz1**2) + 1.0E-15
    ang_current = np.arccos((jx1*jx + jy1*jy + jz1*jz) / (absJ * absJ1))

    ang_current = ang_current * 180 / math.pi 

    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, ang_current, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    cbar1.ax.set_ylabel(r'$\theta(\mathbf{j}, \mathbf{u}$)',
            fontdict=font, fontsize=24)
    cbar1.ax.tick_params(labelsize=24)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    fig = plt.figure(figsize=[7, 5])
    w1, h1 = 0.8, 0.8
    xs, ys = 0.96 - w1, 0.96 - h1
    ax2 = fig.add_axes([xs, ys, w1, h1])
    ang_bins = bins=np.arange(180)
    hist, bin_edges = np.histogram(ang_current, bins=ang_bins, density=True)
    p2 = ax2.plot(hist, linewidth=2)
    ax2.tick_params(labelsize=20)
    ax2.set_xlabel(r'$\theta$', fontdict=font, fontsize=24)
    ax2.set_ylabel(r'$f(\theta)$', fontdict=font, fontsize=24)

    plt.show()
    # plt.close()


def compression_time(pic_info, species, jdote, ylim1, root_dir='../data/'):
    """The time evolution of compression related terms.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
    """
    ntf = pic_info.ntf
    tfields = pic_info.tfields
    fname = root_dir + "compression00_" + species + ".gda"
    fh = open(fname, 'r')
    data = fh.read()
    fh.close()
    compression_data = np.zeros((ntf, 2))
    index_start = 0
    index_end = 4
    for ct in range(ntf):
        for i in range(2):
            compression_data[ct, i], = \
                    struct.unpack('f', data[index_start:index_end])
            index_start = index_end
            index_end += 4
    div_u = compression_data[:, 0]
    pdiv_u = compression_data[:, 1]

    fname = root_dir + "shear00_" + species + ".gda"
    fh = open(fname, 'r')
    data = fh.read()
    fh.close()
    shear_data = np.zeros((ntf, 2))
    index_start = 0
    index_end = 4
    for ct in range(ntf):
        for i in range(2):
            shear_data[ct, i], = \
                    struct.unpack('f', data[index_start:index_end])
            index_start = index_end
            index_end += 4
    bbsigma = shear_data[:, 0]
    pshear = shear_data[:, 1]

    fname = root_dir + "div_vdot_ptensor00_" + species + ".gda"
    fh = open(fname, 'r')
    data = fh.read()
    fh.close()
    data1 = np.zeros((ntf))
    index_start = 0
    index_end = 4
    for ct in range(ntf):
        data1[ct], = struct.unpack('f', data[index_start:index_end])
        index_start = index_end
        index_end += 4
    div_vdot_ptensor = data1[:]

    fname = root_dir + "vdot_div_ptensor00_" + species + ".gda"
    fh = open(fname, 'r')
    data = fh.read()
    fh.close()
    data1 = np.zeros((ntf))
    index_start = 0
    index_end = 4
    for ct in range(ntf):
        data1[ct], = struct.unpack('f', data[index_start:index_end])
        index_start = index_end
        index_end += 4
    vdot_div_ptensor = data1[:]

    ene_bx = pic_info.ene_bx
    enorm = ene_bx[0]
    dtwpe = pic_info.dtwpe
    dtwci = pic_info.dtwci
    dt_fields = pic_info.dt_fields * dtwpe / dtwci
    pdiv_u_cum = np.cumsum(pdiv_u) * dt_fields
    pshear_cum = np.cumsum(pshear) * dt_fields
    div_vdot_ptensor_cum = np.cumsum(div_vdot_ptensor) * dt_fields
    vdot_div_ptensor_cum = np.cumsum(vdot_div_ptensor) * dt_fields
    pdiv_u_cum /= enorm
    pshear_cum /= enorm
    div_vdot_ptensor_cum /= enorm
    vdot_div_ptensor_cum /= enorm

    # jdote = read_jdote_data(species)
    jpolar_dote = jdote.jpolar_dote
    jpolar_dote_int = jdote.jpolar_dote_int
    jqnudote = jdote.jqnupara_dote + jdote.jqnuperp_dote
    jqnudote_cum = jdote.jqnupara_dote_int + jdote.jqnuperp_dote_int
    # jqnudote -= jpolar_dote
    # jqnudote_cum -= jpolar_dote_int
    jqnudote_cum /= enorm

    fig = plt.figure(figsize=[7, 5])
    w1, h1 = 0.8, 0.4
    xs, ys = 0.96-w1, 0.96-h1
    ax = fig.add_axes([xs, ys, w1, h1])
    label1 = r'$-p\nabla\cdot\mathbf{u}$'
    label2 = r'$-(p_\parallel - p_\perp)b_ib_j\sigma_{ij}$'
    label3 = r'$\nabla\cdot(\mathcal{P}\cdot\mathbf{u})$'
    label4 = label3 + label1 + label2
    label5 = r'$\mathbf{u}\cdot(\nabla\cdot\mathcal{P})$'
    label6 = r'$\mathbf{j}_' + species + '\cdot\mathbf{E}$'
    p1 = ax.plot(tfields, pdiv_u, linewidth=2, color='r', label=label1)
    p2 = ax.plot(tfields, pshear, linewidth=2, color='g', label=label2)
    p3 = ax.plot(tfields, div_vdot_ptensor, linewidth=2,
            color='b', label=label3)
    p4 = ax.plot(tfields, pdiv_u + pshear + div_vdot_ptensor,
            linewidth=2, color='darkred', label=label4)
    p5 = ax.plot(tfields, vdot_div_ptensor, linewidth=2, color='k',
            label=label5)
    p6 = ax.plot(tfields, jqnudote, linewidth=2, color='k', linestyle='--',
            label=label6)
    ax.set_ylabel(r'$d\varepsilon_c/dt$', fontdict=font, fontsize=20)
    ax.tick_params(axis='x', labelbottom='off')
    ax.tick_params(labelsize=16)
    tmax = min(np.max(pic_info.tfields), 800)
    ax.set_xlim([0, 800])
    ax.set_ylim(ylim1)

    ax.text(0.45, 0.9, label1, color='red', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax.transAxes)
    ax.text(0.65, 0.9, label2, color='green', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax.transAxes)
    ax.text(0.5, 0.7, label3, color='blue', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax.transAxes)
    ax.text(0.75, 0.7, label5, color='black', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax.transAxes)
    ax.text(0.1, 0.07, label4, color='darkred', fontsize=20, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax.transAxes)

    ys -= h1 + 0.05
    ax1 = fig.add_axes([xs, ys, w1, h1])
    p1 = ax1.plot(tfields, pdiv_u_cum, linewidth=2, color='r')
    p2 = ax1.plot(tfields, pshear_cum, linewidth=2, color='g')
    p3 = ax1.plot(tfields, div_vdot_ptensor_cum, linewidth=2, color='b')
    p3 = ax1.plot(tfields, pdiv_u_cum + pshear_cum + div_vdot_ptensor_cum,
            linewidth=2, color='darkred')
    p5 = ax1.plot(tfields, vdot_div_ptensor_cum, linewidth=2, color='k')
    p6 = ax1.plot(tfields, jqnudote_cum, linewidth=2, color='k',
            linestyle='--', label=label6)
    ax1.set_xlabel(r'$t\Omega_{ci}$', fontdict=font, fontsize=20)
    ax1.set_ylabel(r'$\varepsilon_c$', fontdict=font, fontsize=20)
    ax1.tick_params(labelsize=16)
    ax1.legend(loc=2, prop={'size':20}, ncol=1,
            shadow=False, fancybox=False, frameon=False)
    ax1.set_xlim(ax.get_xlim())
    # ax1.set_ylim(ylim2)
    # if not os.path.isdir('../img/'):
    #     os.makedirs('../img/')
    # fname = '../img/compressional_' + species + '.eps'
    # fig.savefig(fname)
    # plt.show()


def density_ratio(pic_info, current_time):
    """Electron and ion density ratio.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        current_time: current time frame.
    """
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-15, "zt":15}
    fname = "../../data/ne.gda"
    x, z, ne = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/ni.gda"
    x, z, ni = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 

    nx, = x.shape
    nz, = z.shape
    width = 0.75
    height = 0.7
    xs = 0.12
    ys = 0.9 - height
    fig = plt.figure(figsize=[10,4])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":0.5, "vmax":1.5}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, ne/ni,
            ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=24)
    cbar1.ax.set_ylabel(r'$n_e/n_i$',
            fontdict=font, fontsize=24)
    cbar1.ax.tick_params(labelsize=24)
    
    t_wci = current_time*pic_info.dt_fields
    title = r'$t = ' + "{:10.1f}".format(t_wci) + '/\Omega_{ci}$'
    ax1.set_title(title, fontdict=font, fontsize=24)

    # plt.show()
    dir = '../img/img_density_ratio/'
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir(dir):
        os.makedirs(dir)
    fname = 'density_ratio' + str(current_time).zfill(3) + '.jpg'
    fname = dir + fname
    fig.savefig(fname, dpi=300)
    plt.close()


def plot_compression_shear(pic_info, species, current_time):
    """
    Plot compression heating and shear heating terms, compared with j.E

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-50, "zt":50}
    fname = "../../data1/pdiv_u00_" + species + ".gda"
    x, z, pdiv_u = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pshear00_" + species + ".gda"
    x, z, pshear = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    fname = '../../data/u' + species + 'x.gda'
    x, z, ux = read_2d_fields(pic_info, fname, **kwargs) 
    fname = '../../data/u' + species + 'y.gda'
    x, z, uy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = '../../data/u' + species + 'z.gda'
    x, z, uz = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, ex = read_2d_fields(pic_info, '../../data/ex.gda', **kwargs) 
    x, z, ey = read_2d_fields(pic_info, '../../data/ey.gda', **kwargs) 
    x, z, ez = read_2d_fields(pic_info, '../../data/ez.gda', **kwargs) 
    fname = '../../data/n' + species + '.gda'
    x, z, nrho = read_2d_fields(pic_info, fname, **kwargs) 
    if species == 'e':
        jdote = - (ux*ex + uy*ey + uz*ez) * nrho
    else:
        jdote = (ux*ex + uy*ey + uz*ez) * nrho

    pdiv_u_sum = np.sum(pdiv_u, axis=0)
    pdiv_u_cum = np.cumsum(pdiv_u_sum)
    pshear_sum = np.sum(pshear, axis=0)
    pshear_cum = np.cumsum(pshear_sum)
    shear_comp_sum = pdiv_u_sum + pshear_sum
    shear_comp_cum = pdiv_u_cum + pshear_cum
    jdote_sum = np.sum(jdote, axis=0)
    jdote_cum = np.cumsum(jdote_sum)

    nx, = x.shape
    nz, = z.shape
    zl = nz / 4
    zt = nz - zl

    nk = 5
    pdiv_u_new = signal.medfilt2d(pdiv_u, kernel_size=(nk,nk))
    pshear_new = signal.medfilt2d(pshear, kernel_size=(nk,nk))
    jdote_new = signal.medfilt2d(jdote, kernel_size=(nk,nk))
    shear_comp_new = pdiv_u_new + pshear_new

    width = 0.75
    height = 0.2
    xs = 0.12
    ys = 0.98 - height
    gap = 0.025

    fig = plt.figure(figsize=[10,14])
    ax1 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.01, "vmax":0.01}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, pdiv_u_new, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.seismic)
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=20)
    ax1.tick_params(axis='x', labelbottom='off')
    cbar1.set_ticks(np.arange(-0.01, 0.015, 0.01))
    cbar1.ax.tick_params(labelsize=20)
    fname1 = r'$-p\nabla\cdot\mathbf{u}$'
    ax1.text(0.02, 0.8, fname1, color='red', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.01, "vmax":0.01}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p2, cbar2 = plot_2d_contour(x, z, pshear_new, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.seismic)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax2.tick_params(labelsize=20)
    ax2.tick_params(axis='x', labelbottom='off')
    cbar2.set_ticks(np.arange(-0.01, 0.015, 0.01))
    cbar2.ax.tick_params(labelsize=20)
    fname2 = r'$-(p_\parallel - p_\perp)b_ib_j\sigma_{ij}$'
    ax2.text(0.02, 0.8, fname2, color='green', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)
    

    ys -= height + gap
    ax6 = fig.add_axes([xs, ys, width, height])
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.01, "vmax":0.01}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p6, cbar6 = plot_2d_contour(x, z, jdote_new, ax6, fig, **kwargs_plot)
    p6.set_cmap(plt.cm.seismic)
    ax6.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax6.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax6.tick_params(labelsize=20)
    ax6.tick_params(axis='x', labelbottom='off')
    cbar6.set_ticks(np.arange(-0.01, 0.015, 0.01))
    cbar6.ax.tick_params(labelsize=20)
    fname6 = r'$' + '\mathbf{j}_' + species + '\cdot\mathbf{E}' + '$'
    ax6.text(0.02, 0.8, fname6, color='black', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax6.transAxes)

    ys -= height + gap
    w1, h1 = fig.get_size_inches()
    width1 = width * 0.98 - 0.05 / w1
    ax7 = fig.add_axes([xs, ys, width1, height])
    ax7.plot(x, pdiv_u_cum, linewidth=2, color='r')
    ax7.plot(x, pshear_cum, linewidth=2, color='g')
    ax7.plot(x, shear_comp_cum, linewidth=2, color='b')
    ax7.plot(x, jdote_cum, linewidth=2, color='k', linestyle='-.')
    xmax = np.max(x)
    xmin = np.min(x)
    # ax7.set_ylim([-0.2, 0.2])
    ax7.plot([xmin, xmax], [0, 0], color='k', linestyle='--')
    ax7.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax7.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax7.tick_params(labelsize=20)

    # width = 0.75
    # height = 0.73
    # xs = 0.12
    # ys = 0.96 - height
    # fig = plt.figure(figsize=[10,3])
    # ax1 = fig.add_axes([xs, ys, width, height])
    # kwargs_plot = {"xstep":1, "zstep":1, "vmin":-0.1, "vmax":0.1}
    # xstep = kwargs_plot["xstep"]
    # zstep = kwargs_plot["zstep"]
    # p1, cbar1 = plot_2d_contour(x, z, div_u, ax1, fig, **kwargs_plot)
    # p1.set_cmap(plt.cm.seismic)
    # ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
    #         colors='black', linewidths=0.5)
    # ax1.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    # ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    # ax1.tick_params(labelsize=20)
    # cbar1.ax.tick_params(labelsize=20)
    
    plt.show()
    # if not os.path.isdir('../img/'):
    #     os.makedirs('../img/')
    # if not os.path.isdir('../img/img_compression/'):
    #     os.makedirs('../img/img_compression/')
    # fname = 'compression' + str(current_time).zfill(3) + '_' + species + '.jpg'
    # fname = '../img/img_compression/' + fname
    # fig.savefig(fname)
    # plt.close()


def plot_shear(pic_info, species, current_time):
    """
    Plot shear heating terms.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-20, "zt":20}
    fname = "../../data1/pshear00_" + species + ".gda"
    x, z, pshear = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/bbsigma00_" + species + ".gda"
    x, z, bbsigma = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/ppara00_" + species + ".gda"
    x, z, ppara = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pperp00_" + species + ".gda"
    x, z, pperp = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 

    nx, = x.shape
    nz, = z.shape
    nk = 5
    # pshear_new = signal.medfilt2d(pshear, kernel_size=(nk,nk))
    # bbsigma_new = signal.medfilt2d(bbsigma, kernel_size=(nk,nk))
    kernel = np.ones((nk,nk)) / float(nk*nk)
    pshear_new = signal.convolve2d(pshear, kernel, mode='same')
    bbsigma_new = signal.convolve2d(bbsigma, kernel, mode='same')
    pshear_sum = np.sum(pshear_new, axis=0)
    pshear_cum = np.cumsum(pshear_sum)

    width = 0.78
    height = 0.19
    xs = 0.12
    ys = 0.97 - height
    gap = 0.04

    fig = plt.figure(figsize=[10,8])
    ax1 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.04, 0.04
    else:
        vmin, vmax = -0.02, 0.02
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, bbsigma_new, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=20)
    ax1.tick_params(axis='x', labelbottom='off')
    cbar1.set_ticks(np.arange(vmin, vmax+0.01, 0.02))
    cbar1.ax.tick_params(labelsize=20)
    fname1 = r'$b_ib_j\sigma_{ij}$'
    ax1.text(0.02, 0.8, fname1, color='red', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.4, 0.4
    else:
        vmin, vmax = -0.8, 0.8
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p2, cbar2 = plot_2d_contour(x, z, -ppara+pperp, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.seismic)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax2.tick_params(labelsize=20)
    if species == 'e':
        cbar2.set_ticks(np.arange(vmin, vmax+0.1, 0.2))
    else:
        cbar2.set_ticks(np.arange(vmin, vmax+0.1, 0.4))
    cbar2.ax.tick_params(labelsize=20)
    ax2.tick_params(axis='x', labelbottom='off')
    fname2 = r'$-(p_\parallel - p_\perp)$'
    ax2.text(0.02, 0.8, fname2, color='blue', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)

    ys -= height + gap
    ax3 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.002, 0.002
    else:
        vmin, vmax = -0.004, 0.004
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p3, cbar3 = plot_2d_contour(x, z, pshear_new, ax3, fig, **kwargs_plot)
    p3.set_cmap(plt.cm.seismic)
    ax3.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax3.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax3.tick_params(labelsize=20)
    ax3.tick_params(axis='x', labelbottom='off')
    cbar3.set_ticks(np.arange(vmin, vmax+0.001, 0.002))
    cbar3.ax.tick_params(labelsize=20)
    fname2 = r'$-(p_\parallel - p_\perp)b_ib_j\sigma_{ij}$'
    ax3.text(0.02, 0.8, fname2, color='green', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax3.transAxes)
    
    ys -= height + gap
    w1, h1 = fig.get_size_inches()
    width1 = width * 0.98 - 0.05 / w1
    ax4 = fig.add_axes([xs, ys, width1, height])
    p4 = ax4.plot(x, pshear_sum, color='green', linewidth=1)
    p41 = ax4.plot([np.min(x), np.max(x)], [0, 0], color='black', linestyle='--')
    ax4.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax4.set_ylabel(r'$-(p_\parallel - p_\perp)b_ib_j\sigma_{ij}$',
            fontdict=font, fontsize=24)
    ax4.tick_params(labelsize=20)
    
    # plt.show()
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir('../img/img_compression/'):
        os.makedirs('../img/img_compression/')
    dir = '../img/img_compression/shear_only/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    fname = 'shear' + str(current_time).zfill(3) + '_' + species + '.jpg'
    fname = dir + fname
    fig.savefig(fname, dpi=400)
    plt.close()


def plot_compression_only(pic_info, species, current_time):
    """
    Plot compressional heating terms.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    kwargs = {"current_time":current_time, "xl":0, "xr":200, "zb":-20, "zt":20}
    fname = "../../data1/div_u00_" + species + ".gda"
    x, z, div_u = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pdiv_u00_" + species + ".gda"
    x, z, pdiv_u = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/ppara00_" + species + ".gda"
    x, z, ppara = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data1/pperp00_" + species + ".gda"
    x, z, pperp = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    pscalar = (ppara + 2 * pperp) / 3.0

    nx, = x.shape
    nz, = z.shape
    nk = 5
    # div_u_new = signal.medfilt2d(div_u, kernel_size=(nk,nk))
    # pdiv_u_new = signal.medfilt2d(pdiv_u, kernel_size=(nk,nk))
    kernel = np.ones((nk,nk)) / float(nk*nk)
    div_u_new = signal.convolve2d(div_u, kernel, mode='same')
    pdiv_u_new = signal.convolve2d(pdiv_u, kernel, mode='same')
    pdiv_u_sum = np.sum(pdiv_u_new, axis=0)
    pdiv_u_cum = np.cumsum(pdiv_u_sum)

    width = 0.78
    height = 0.19
    xs = 0.12
    ys = 0.97 - height
    gap = 0.04

    fig = plt.figure(figsize=[10,8])
    ax1 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.04, 0.04
    else:
        vmin, vmax = -0.02, 0.02
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, div_u_new, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=20)
    ax1.tick_params(axis='x', labelbottom='off')
    cbar1.set_ticks(np.arange(vmin, vmax+0.01, 0.02))
    cbar1.ax.tick_params(labelsize=20)
    fname1 = r'$\nabla\cdot\mathbf{u}$'
    ax1.text(0.02, 0.8, fname1, color='red', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmax = 0.6
    else:
        vmax = 1.0
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":0, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p2, cbar2 = plot_2d_contour(x, z, pscalar, ax2, fig, **kwargs_plot)
    # p2.set_cmap(plt.cm.seismic)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='white', linewidths=0.5)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax2.tick_params(labelsize=20)
    cbar2.set_ticks(np.arange(0, vmax + 0.1, 0.2))
    cbar2.ax.tick_params(labelsize=20)
    ax2.tick_params(axis='x', labelbottom='off')
    fname2 = r'$p$'
    ax2.text(0.02, 0.8, fname2, color='red', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)

    ys -= height + gap
    ax3 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.004, 0.004
    else:
        vmin, vmax = -0.002, 0.002
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p3, cbar3 = plot_2d_contour(x, z, pdiv_u_new, ax3, fig, **kwargs_plot)
    p3.set_cmap(plt.cm.seismic)
    ax3.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax3.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax3.tick_params(labelsize=20)
    ax3.tick_params(axis='x', labelbottom='off')
    cbar3.set_ticks(np.arange(vmin, vmax+0.001, 0.002))
    cbar3.ax.tick_params(labelsize=20)
    fname2 = r'$-p\nabla\cdot\mathbf{u}$'
    ax3.text(0.02, 0.8, fname2, color='green', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax3.transAxes)

    ys -= height + gap
    w1, h1 = fig.get_size_inches()
    width1 = width * 0.98 - 0.05 / w1
    ax4 = fig.add_axes([xs, ys, width1, height])
    p4 = ax4.plot(x, pdiv_u_sum, color='green', linewidth=1)
    p41 = ax4.plot([np.min(x), np.max(x)], [0, 0], color='black', linestyle='--')
    ax4.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax4.set_ylabel(r'$-p\nabla\cdot\mathbf{u}$', fontdict=font, fontsize=24)
    ax4.tick_params(labelsize=20)
    
    # plt.show()
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir('../img/img_compression/'):
        os.makedirs('../img/img_compression/')
    dir = '../img/img_compression/compression_only/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    fname = 'compression' + str(current_time).zfill(3) + '_' + species + '.jpg'
    fname = dir + fname
    fig.savefig(fname, dpi=400)
    plt.close()


def plot_velocity_field(pic_info, species, current_time):
    """
    Plot velocity field.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    zb, zt = -20, 20
    xl, xr = 0, 200
    kwargs = {"current_time":current_time, "xl":xl, "xr":xr, "zb":zb, "zt":zt}
    fname = "../../data/u" + species + "x.gda"
    x, z, ux = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/u" + species + "z.gda"
    x, z, uz = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    # X, Z = np.meshgrid(x, z)
    speed = np.sqrt(ux**2 + uz**2)
    nx, = x.shape
    nz, = z.shape

    width = 0.88
    height = 0.85
    xs = 0.06
    ys = 0.96 - height
    gap = 0.04

    fig = plt.figure(figsize=[20,8])
    ax = fig.add_axes([xs, ys, width, height])
    p1 = ax.streamplot(x, z, ux, uz, color=speed, linewidth=1,
            density=5.0, cmap=plt.cm.jet, arrowsize=1.0)
    kwargs_plot = {"xstep":2, "zstep":2}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    ax.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax.set_xlim([xl, xr])
    ax.set_ylim([zb, zt])
    ax.tick_params(labelsize=20)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.05)
    cbar = fig.colorbar(p1.lines, cax=cax)
    cbar.ax.tick_params(labelsize=20)
    fname = r'$u_' + species + '$'
    cbar.ax.set_ylabel(fname, fontdict=font, fontsize=24)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir('../img/img_velocity_field/'):
        os.makedirs('../img/img_velocity_field/')
    fname = 'u' + species + '_' + str(current_time).zfill(3) + '.jpg'
    fname = '../img/img_velocity_field/' + fname
    fig.savefig(fname)
    # plt.show()
    plt.close()


def plot_velocity_components(pic_info, species, current_time):
    """
    Plot the 2D contour of the 3 components of the velocity field.

    Args:
        pic_info: namedtuple for the PIC simulation information.
        species: 'e' for electrons, 'i' for ions.
        current_time: current time frame.
    """
    print(current_time)
    zb, zt = -20, 20
    xl, xr = 0, 200
    kwargs = {"current_time":current_time, "xl":xl, "xr":xr, "zb":zb, "zt":zt}
    fname = "../../data/u" + species + "x.gda"
    x, z, ux = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/u" + species + "y.gda"
    x, z, uy = read_2d_fields(pic_info, fname, **kwargs) 
    fname = "../../data/u" + species + "z.gda"
    x, z, uz = read_2d_fields(pic_info, fname, **kwargs) 
    x, z, Ay = read_2d_fields(pic_info, "../../data/Ay.gda", **kwargs) 
    nx, = x.shape
    nz, = z.shape

    width = 0.8
    height = 0.26
    xs = 0.12
    ys = 0.96 - height
    gap = 0.04

    fig = plt.figure(figsize=[10,8])
    ax1 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.3, 0.3
    else:
        vmin, vmax = -0.2, 0.2
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p1, cbar1 = plot_2d_contour(x, z, ux, ax1, fig, **kwargs_plot)
    p1.set_cmap(plt.cm.get_cmap('seismic'))
    ax1.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax1.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax1.tick_params(labelsize=20)
    ax1.tick_params(axis='x', labelbottom='off')
    cbar1.set_ticks(np.arange(vmin, vmax+0.1, 0.1))
    cbar1.ax.tick_params(labelsize=20)
    fname1 = r'$u_x$'
    ax1.text(0.02, 0.8, fname1, color='black', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax1.transAxes)

    ys -= height + gap
    ax2 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.3, 0.3
    else:
        vmin, vmax = -0.2, 0.2
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p2, cbar2 = plot_2d_contour(x, z, uy, ax2, fig, **kwargs_plot)
    p2.set_cmap(plt.cm.seismic)
    ax2.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='white', linewidths=0.5)
    ax2.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax2.tick_params(labelsize=20)
    cbar2.set_ticks(np.arange(vmin, vmax+0.1, 0.1))
    cbar2.ax.tick_params(labelsize=20)
    ax2.tick_params(axis='x', labelbottom='off')
    fname2 = r'$u_y$'
    ax2.text(0.02, 0.8, fname2, color='black', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax2.transAxes)

    ys -= height + gap
    ax3 = fig.add_axes([xs, ys, width, height])
    if species == 'e':
        vmin, vmax = -0.3, 0.3
    else:
        vmin, vmax = -0.2, 0.2
    kwargs_plot = {"xstep":1, "zstep":1, "vmin":vmin, "vmax":vmax}
    xstep = kwargs_plot["xstep"]
    zstep = kwargs_plot["zstep"]
    p3, cbar3 = plot_2d_contour(x, z, uz, ax3, fig, **kwargs_plot)
    p3.set_cmap(plt.cm.seismic)
    ax3.contour(x[0:nx:xstep], z[0:nz:zstep], Ay[0:nz:zstep, 0:nx:xstep], 
            colors='black', linewidths=0.5)
    ax3.set_xlabel(r'$x/d_i$', fontdict=font, fontsize=24)
    ax3.set_ylabel(r'$z/d_i$', fontdict=font, fontsize=24)
    ax3.tick_params(labelsize=20)
    cbar3.set_ticks(np.arange(vmin, vmax+0.1, 0.1))
    cbar3.ax.tick_params(labelsize=20)
    fname2 = r'$u_z$'
    ax3.text(0.02, 0.8, fname2, color='black', fontsize=24, 
            bbox=dict(facecolor='none', alpha=1.0, edgecolor='none', pad=10.0),
            horizontalalignment='left', verticalalignment='center',
            transform = ax3.transAxes)

    # plt.show()
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    if not os.path.isdir('../img/img_uxyz/'):
        os.makedirs('../img/img_uxyz/')
    fname = 'u' + species + '_' + str(current_time).zfill(3) + '.jpg'
    fname = '../img/img_uxyz/' + fname
    fig.savefig(fname)
    plt.close()


def move_compression():
    if not os.path.isdir('../data/'):
        os.makedirs('../data/')
    dir = '../data/compression/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    base_dirs, run_names = ApJ_long_paper_runs()
    for base_dir, run_name in zip(base_dirs, run_names):
        fpath = dir + run_name
        if not os.path.isdir(fpath):
            os.makedirs(fpath)
        command = "cp " + base_dir + "/pic_analysis/data/compression00* " + fpath
        os.system(command)
        command = "cp " + base_dir + "/pic_analysis/data/shear00* " + fpath
        os.system(command)
        command = "cp " + base_dir + "/pic_analysis/data/div_vdot_ptensor00* " + fpath
        os.system(command)
        command = "cp " + base_dir + "/pic_analysis/data/vdot_div_ptensor00* " + fpath
        os.system(command)


def plot_compression_time_multi(species):
    """Plot time evolution of compression and shear heating for multiple runs

    Args:
        species: particle species
    """
    dir = '../data/compression/'
    dir_jdote = '../data/jdote_data/'
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    odir = '../img/compression/'
    if not os.path.isdir(odir):
        os.makedirs(odir)
    base_dirs, run_names = ApJ_long_paper_runs()
    nrun = len(run_names)
    ylim1 = np.zeros((nrun, 2))
    if species == 'e':
        ylim1[0, :] = -0.05, 0.15
        ylim1[1, :] = -0.3, 1.1
        ylim1[2, :] = -1.0, 5
        ylim1[3, :] = -10.0, 30.0
        ylim1[4, :] = -2.0, 5.0
        ylim1[5, :] = -0.1, 0.2
        ylim1[6, :] = -0.5, 1.1
        ylim1[7, :] = -3.0, 6.0
        ylim1[8, :] = -1.0, 5.0
    else:
        ylim1[0, :] = -0.1, 0.25
        ylim1[1, :] = -0.6, 2.2
        ylim1[2, :] = -2.0, 10
        ylim1[3, :] = -20.0, 60.0
        ylim1[4, :] = -4.0, 13.0
        ylim1[5, :] = -0.2, 0.4
        ylim1[6, :] = -1.0, 2.2
        ylim1[7, :] = -5.0, 15.0
        ylim1[8, :] = -3.0, 7.0
    for i in range(nrun):
        run_name = run_names[i]
        picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
        jdote_fname = dir_jdote + 'jdote_' + run_name + '_' + species + '.json'
        pic_info = read_data_from_json(picinfo_fname)
        jdote_data = read_data_from_json(jdote_fname)
        fpath_comp = '../data/compression/' + run_name + '/'
        compression_time(pic_info, species, jdote_data, ylim1[i,:], fpath_comp)
        # oname = odir + 'compression_' + run_name + '_' + species + '.eps'
        oname = odir + 'compression_' + run_name + '_wjp_' + species + '.eps'
        plt.savefig(oname)
        # plt.show()
        plt.close()


if __name__ == "__main__":
    # pic_info = pic_information.get_pic_info('../../')
    # ntp = pic_info.ntp
    # for i in range(pic_info.ntf):
    #     plot_compression(pic_info, 'i', i)
    # plot_compression(pic_info, 'e', 40)
    # plot_shear(pic_info, 'e', 40)
    # for ct in range(pic_info.ntf):
    #     plot_shear(pic_info, 'i', ct)
    # plot_compression_only(pic_info, 'i', 40)
    # for ct in range(pic_info.ntf):
    #     plot_compression_only(pic_info, 'e', ct)
    # plot_velocity_field(pic_info, 'e', 15)
    # for ct in range(pic_info.ntf):
    #     plot_velocity_field(pic_info, 'e', ct)
    # for ct in range(pic_info.ntf):
    #     plot_velocity_field(pic_info, 'i', ct)
    # plot_compression_shear(pic_info, 'e', 24)
    # plot_compression_cut(pic_info, 'i', 12)
    # angle_current(pic_info, 12)
    # compression_time(pic_info, 'e')
    # density_ratio(pic_info, 8)
    # for ct in range(pic_info.ntf):
    #     density_ratio(pic_info, ct)
    # plot_velocity_components(pic_info, 'e', 40)
    # for ct in range(pic_info.ntf):
    #     plot_velocity_components(pic_info, 'e', ct)
    # for ct in range(pic_info.ntf):
    #     plot_velocity_components(pic_info, 'i', ct)
    # move_compression()
    plot_compression_time_multi('i')
