"""
Analysis procedures to calculate power spectrum
"""
import collections
import math
import multiprocessing
import os.path
import struct

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from joblib import Parallel, delayed
from matplotlib import rc
from matplotlib.colors import LogNorm
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.mplot3d import Axes3D

import palettable
import pic_information
from contour_plots import plot_2d_contour, read_2d_fields
from energy_conversion import read_data_from_json
from shell_functions import mkdir_p

rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
mpl.rc('text', usetex=True)
mpl.rcParams['text.latex.preamble'] = [r"\usepackage{amsmath}"]

font = {
    'family': 'serif',
    #'color'  : 'darkred',
    'color': 'black',
    'weight': 'normal',
    'size': 24,
}

colors = palettable.colorbrewer.qualitative.Set1_9.mpl_colors

# colors = palettable.colorbrewer.qualitative.Dark2_8.mpl_colors


def calc_power_spectrum_mag(pic_info,
                            ct,
                            run_name,
                            shock_pos,
                            base_dir='../../'):
    """calculate power spectrum using magnetic fields

    Args:
        pic_info: namedtuple for the PIC simulation information.
        ct: current time frame.
    """
    xmin, xmax = 0, pic_info.lx_di
    xmin, xmax = 0, 105
    zmin, zmax = -0.5 * pic_info.lz_di, 0.5 * pic_info.lz_di
    kwargs = {
        "current_time": ct,
        "xl": xmin,
        "xr": xmax,
        "zb": zmin,
        "zt": zmax
    }
    fname = base_dir + 'data1/vex.gda'
    x, z, vel = read_2d_fields(pic_info, fname, **kwargs)
    nx, = x.shape
    nz, = z.shape
    # data_cum = np.sum(vel, axis=0) / nz
    # data_grad = np.abs(np.gradient(data_cum))
    # xs = 5
    # max_index = np.argmax(data_grad[xs:])
    # xm = x[max_index]
    xm = x[shock_pos]

    xmin, xmax = 0, xm
    fname = base_dir + 'data1/bx.gda'
    x, z, bx = read_2d_fields(pic_info, fname, **kwargs)
    fname = base_dir + 'data1/by.gda'
    x, z, by = read_2d_fields(pic_info, fname, **kwargs)
    fname = base_dir + 'data1/bz.gda'
    x, z, bz = read_2d_fields(pic_info, fname, **kwargs)
    smime = math.sqrt(pic_info.mime)
    lx = np.max(x) - np.min(x)
    lz = np.max(z) - np.min(z)

    bx_k = np.fft.rfft2(bx)
    by_k = np.fft.rfft2(by)
    bz_k = np.fft.rfft2(bz)
    b2_k = np.absolute(bx_k)**2 + np.absolute(by_k)**2 + np.absolute(bz_k)**2
    xstep = lx / nx
    kx = np.fft.fftfreq(nx, xstep)
    idx = np.argsort(kx)
    zstep = lz / nz
    kz = np.fft.fftfreq(nz, zstep)
    idz = np.argsort(kz)
    print np.min(kx), np.max(kx), np.min(kz), np.max(kz)

    kxs, kzs = np.meshgrid(kx[:nx // 2 + 1], kz)
    ks = np.sqrt(kxs * kxs + kzs * kzs)
    # kmin, kmax = np.min(ks), np.max(ks)
    # kbins = np.linspace(kmin, kmax, nx//2+1, endpoint=True)
    kmin = 1E-2
    kmax = np.max(ks)
    kmin_log, kmax_log = math.log10(kmin), math.log10(kmax)
    kbins = 10**np.linspace(kmin_log, kmax_log, 64, endpoint=True)
    ps, kbins_edges = np.histogram(
        ks, bins=kbins, weights=b2_k * ks, density=True)
    w1, h1 = 0.8, 0.8
    xs, ys = 0.15, 0.95 - h1
    fig = plt.figure(figsize=[7, 5])
    ax1 = fig.add_axes([xs, ys, w1, h1])
    for index, k in np.ndenumerate(kbins):
        pass
        # print index, k
    psm = 25
    # pindex = -5.0/3.0
    pindex = -2.0
    power_k = kbins[psm:]**pindex
    shift = 22
    ax1.loglog(kbins_edges[:-1], ps, linewidth=2)
    ax1.loglog(
        kbins[psm:psm + shift],
        power_k[:shift] * 2 / power_k[0],
        linestyle='--',
        linewidth=2,
        color='k')
    # power_index = "{%0.2f}" % pindex
    power_index = '-2.0'
    tname = r'$\sim k^{' + power_index + '}$'
    ax1.text(
        0.45,
        0.7,
        tname,
        color='black',
        fontsize=24,
        horizontalalignment='left',
        verticalalignment='center',
        transform=ax1.transAxes)
    ax1.tick_params(labelsize=16)
    ax1.set_xlabel(r'$kd_i$', fontdict=font, fontsize=20)
    ax1.set_ylabel(r'$E_B(k)$', fontdict=font, fontsize=20)
    ax1.set_xlim([1E-2, 3E1])
    ax1.set_ylim([1E-3, 3E1])

    fig_dir = '../img/img_power_spectrum/' + run_name + '/'
    mkdir_p(fig_dir)
    fname = fig_dir + '/ps_mag_' + str(ct).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=300)

    # plt.show()
    plt.close()


def calc_power_spectrum_vel(pic_info,
                            ct,
                            species,
                            run_name,
                            shock_pos,
                            base_dir='../../'):
    """Calculate power spectrum using velocities

    Args:
        pic_info: namedtuple for the PIC simulation information.
        ct: current time frame.
        species: particle species
        run_name: the simulation run name
        shock_pos: the shock position in cell index
        base_dir: the root directory of the run
    """
    xmin, xmax = 0, pic_info.lx_di
    xmin, xmax = 0, 105
    zmin, zmax = -0.5 * pic_info.lz_di, 0.5 * pic_info.lz_di
    kwargs = {
        "current_time": ct,
        "xl": xmin,
        "xr": xmax,
        "zb": zmin,
        "zt": zmax
    }
    fname = base_dir + 'data1/vex.gda'
    x, z, vel = read_2d_fields(pic_info, fname, **kwargs)
    nx, = x.shape
    nz, = z.shape
    xm = x[shock_pos]

    xmin, xmax = 0, xm
    fname = base_dir + 'data1/v' + species + 'x.gda'
    x, z, vx = read_2d_fields(pic_info, fname, **kwargs)
    fname = base_dir + 'data1/v' + species + 'y.gda'
    x, z, vy = read_2d_fields(pic_info, fname, **kwargs)
    fname = base_dir + 'data1/v' + species + 'z.gda'
    x, z, vz = read_2d_fields(pic_info, fname, **kwargs)
    smime = math.sqrt(pic_info.mime)
    lx = np.max(x) - np.min(x)
    lz = np.max(z) - np.min(z)

    vx_k = np.fft.rfft2(vx)
    vy_k = np.fft.rfft2(vy)
    vz_k = np.fft.rfft2(vz)
    v2_k = np.absolute(vx_k)**2 + np.absolute(vy_k)**2 + np.absolute(vz_k)**2
    xstep = lx / nx
    kx = np.fft.fftfreq(nx, xstep)
    idx = np.argsort(kx)
    zstep = lz / nz
    kz = np.fft.fftfreq(nz, zstep)
    idz = np.argsort(kz)
    print np.min(kx), np.max(kx), np.min(kz), np.max(kz)

    kxs, kzs = np.meshgrid(kx[:nx // 2 + 1], kz)
    ks = np.sqrt(kxs * kxs + kzs * kzs)
    kmin, kmax = np.min(ks), np.max(ks)
    kbins = np.linspace(kmin, kmax, nx // 2 + 1, endpoint=True)
    ps, kbins_edges = np.histogram(
        ks, bins=kbins, weights=v2_k * ks, normed=True)
    w1, h1 = 0.8, 0.8
    xs, ys = 0.15, 0.95 - h1
    fig = plt.figure(figsize=[7, 5])
    ax1 = fig.add_axes([xs, ys, w1, h1])
    ax1.loglog(kbins_edges[:-1], ps, linewidth=2)
    # psm = np.argmax(ps)
    psm = 4
    pindex = -5.0 / 3
    power_k = kbins[psm:]**pindex
    shift = 400
    if species is 'electron':
        ax1.loglog(
            kbins[psm:psm + shift],
            power_k[:shift] * 0.5 / power_k[0],
            linestyle='--',
            linewidth=2,
            color='k')
    else:
        ax1.loglog(
            kbins[psm:psm + shift],
            power_k[:shift] * 10 / power_k[0],
            linestyle='--',
            linewidth=2,
            color='k')
    power_index = "{%0.1f}" % pindex
    # tname = r'$\sim k^{' + power_index + '}$'
    tname = r'$\sim k^{-5/3}$'
    ax1.text(
        0.4,
        0.8,
        tname,
        color='black',
        fontsize=24,
        horizontalalignment='left',
        verticalalignment='center',
        transform=ax1.transAxes)
    ax1.tick_params(labelsize=16)
    ax1.set_xlabel(r'$kd_i$', fontdict=font, fontsize=20)
    ax1.set_ylabel(r'$E_V(k)$', fontdict=font, fontsize=20)
    ax1.set_xlim([1E-2, 3E1])
    if species is 'electron':
        ax1.set_ylim([1E-2, 0.5])
    else:
        ax1.set_ylim([1E-2, 5])

    fig_dir = '../img/img_power_spectrum/' + run_name + '/'
    mkdir_p(fig_dir)
    # fname = fig_dir + '/ps_vel_' + species + str(ct).zfill(3) + '.jpg'
    # fig.savefig(fname, dpi=300)

    plt.show()
    # plt.close()


def calc_avg_bfield(pic_info, ct, run_name, xm, base_dir='../../'):
    """Calculate the average magnetic field in the shock downstream

    Args:
        pic_info: namedtuple for the PIC simulation information.
        ct: current time frame.
        run_name: the simulation run name
        xm: the shock position in di
        base_dir: the root directory of the run
    """
    xmin, xmax = 0, pic_info.lx_di
    xmin, xmax = 0, 105
    zmin, zmax = -0.5 * pic_info.lz_di, 0.5 * pic_info.lz_di
    kwargs = {
        "current_time": ct,
        "xl": xmin,
        "xr": xmax,
        "zb": zmin,
        "zt": zmax
    }
    xmin, xmax = 0, xm
    fname = base_dir + 'data1/bx.gda'
    x, z, bx = read_2d_fields(pic_info, fname, **kwargs)
    fname = base_dir + 'data1/by.gda'
    x, z, by = read_2d_fields(pic_info, fname, **kwargs)
    fname = base_dir + 'data1/bz.gda'
    x, z, bz = read_2d_fields(pic_info, fname, **kwargs)

    bx_avg = np.average(bx)
    by_avg = np.average(by)
    bz_avg = np.average(bz)

    bavg = np.asarray([bx_avg, by_avg, bz_avg])

    data_dir = '../data/b_average/'
    mkdir_p(data_dir)
    fname = data_dir + 'bavg_' + str(ct) + '.txt'
    bavg.tofile(fname)


def plot_avg_bfiled(pic_info):
    """Plot average magnetic field in the shock downstream
    """
    ts = 10
    cts = range(ts, pic_info.ntf - 1)
    nt = len(cts)
    bavg = np.zeros((nt, 3))
    data_dir = '../data/b_average/'
    for ct in cts:
        fname = data_dir + 'bavg_' + str(ct) + '.txt'
        bavg[ct - ts] = np.fromfile(fname)

    plt.plot(bavg[:, 0], linewidth=2, color='r')
    plt.plot(bavg[:, 1], linewidth=2, color='g')
    plt.plot(bavg[:, 2], linewidth=2, color='b')
    plt.show()


def div0(a, b):
    """ ignore / 0, div0( [-1, 0, 1], 0 ) -> [0, 0, 0] 

    From: http://stackoverflow.com/a/35696047/2561161

    """
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.true_divide(a, b)
        c[~np.isfinite(c)] = 0  # -inf inf NaN
    return c


def calc_power_spectrum_vel_comp(pic_info,
                                 ct,
                                 species,
                                 run_name,
                                 xshock,
                                 base_dir='../../',
                                 single_file=True):
    """Calculate power spectrum of compressible mode and incompressible mode

    Args:
        pic_info: namedtuple for the PIC simulation information.
        ct: current time frame.
        species: particle species
        run_name: the simulation run name
        xshock: the shock position along the x-direction in di
        base_dir: the root directory of the run
    """
    xmin, xmax = 0, pic_info.lx_di
    xmin, xmax = 0, 105
    zmin, zmax = -0.5 * pic_info.lz_di, 0.5 * pic_info.lz_di

    xmin, xmax = 0, xshock
    if single_file:
        kwargs = {
            "current_time": ct,
            "xl": xmin,
            "xr": xmax,
            "zb": zmin,
            "zt": zmax
        }
        fname = base_dir + 'data1/v' + species + 'x.gda'
        x, z, vx = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data1/v' + species + 'y.gda'
        x, z, vy = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data1/v' + species + 'z.gda'
        x, z, vz = read_2d_fields(pic_info, fname, **kwargs)
    else:
        kwargs = {
            "current_time": 0,
            "xl": xmin,
            "xr": xmax,
            "zb": zmin,
            "zt": zmax
        }
        fields_interval = pic_info.fields_interval
        tframe = str(fields_interval * ct)
        fname = base_dir + 'data/v' + species + 'x_' + tframe + '.gda'
        x, z, vx = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data/v' + species + 'y_' + tframe + '.gda'
        x, z, vy = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data/v' + species + 'z_' + tframe + '.gda'
        x, z, vz = read_2d_fields(pic_info, fname, **kwargs)
    nx, = x.shape
    nz, = z.shape
    smime = math.sqrt(pic_info.mime)
    lx = np.max(x) - np.min(x)
    lz = np.max(z) - np.min(z)

    vx_k = np.fft.rfft2(vx)
    vy_k = np.fft.rfft2(vy)
    vz_k = np.fft.rfft2(vz)
    xstep = lx / nx
    kx = np.fft.fftfreq(nx, xstep)
    idx = np.argsort(kx)
    zstep = lz / nz
    kz = np.fft.fftfreq(nz, zstep)
    idz = np.argsort(kz)
    print np.min(kx), np.max(kx), np.min(kz), np.max(kz)

    kxs, kzs = np.meshgrid(kx[:nx // 2 + 1], kz)
    k = np.sqrt(kxs * kxs + kzs * kzs)

    vkpara = div0(vx_k * kxs + vz_k * kzs, k)
    vkperp_x = div0(-vy_k * kzs, k)
    vkperp_y = div0(vx_k * kzs - vz_k * kxs, k)
    vkperp_z = div0(vy_k * kxs, k)

    v2_k = np.absolute(vx_k)**2 + np.absolute(vy_k)**2 + np.absolute(vz_k)**2
    v2_kpara = np.absolute(vkpara)**2
    v2_kperp = np.absolute(vkperp_x)**2 + np.absolute(vkperp_y)**2 + \
               np.absolute(vkperp_z)**2

    kxs, kzs = np.meshgrid(kx[:nx // 2 + 1], kz)
    ks = np.sqrt(kxs * kxs + kzs * kzs)
    kmin, kmax = np.min(ks), np.max(ks)
    kmin = 1E-2
    kmin_log = math.log10(kmin)
    kmax_log = math.log10(kmax)
    # kbins = np.linspace(kmin, kmax, 256, endpoint=True)
    kbins = 10**np.linspace(kmin_log, kmax_log, 64, endpoint=True)
    ps, kbins_edges = np.histogram(ks, bins=kbins, weights=v2_k * ks)
    ps_para, kbins_edges = np.histogram(ks, bins=kbins, weights=v2_kpara * ks)
    ps_perp, kbins_edges = np.histogram(ks, bins=kbins, weights=v2_kperp * ks)
    power1 = ps / np.diff(kbins_edges)
    power2 = ps_para / np.diff(kbins_edges)
    power3 = ps_perp / np.diff(kbins_edges)
    # print power1
    # print (power1 + 1E-5) / (power2 + power3 + 1E-5)
    # print (np.sum(ps)) / (np.sum(ps_para) + np.sum(ps_perp))
    # print (np.sum(ps*np.diff(kbins_edges)))
    # print (np.sum(ps_para*np.diff(kbins_edges)))
    # print (np.sum(ps_perp*np.diff(kbins_edges)))
    w1, h1 = 0.8, 0.8
    xs, ys = 0.15, 0.95 - h1
    fig = plt.figure(figsize=[7, 5])
    ax1 = fig.add_axes([xs, ys, w1, h1])
    ax1.loglog(kbins_edges[:-1], power1, linewidth=2, label='Total')
    ax1.loglog(kbins_edges[:-1], power2, linewidth=2, label='Compressible')
    ax1.loglog(kbins_edges[:-1], power3, linewidth=2, label='Incompressible')
    # psm = np.argmax(ps)
    psm = 5
    pindex = -5.0 / 3
    power_k = kbins[psm:]**pindex
    shift = 20
    if species is 'electron':
        ax1.loglog(
            kbins[psm:psm + shift],
            power_k[:shift] * 0.5 / power_k[0],
            linestyle='--',
            linewidth=2,
            color='k')
    else:
        index_s = 20
        index_ps = index_s - psm
        ax1.loglog(
            kbins[index_s:index_s + shift],
            power_k[index_ps:shift + index_ps] * 1E12 / power_k[index_ps],
            linestyle='--',
            linewidth=2,
            color='k')
    power_index = "{%0.1f}" % pindex
    # tname = r'$\sim k^{' + power_index + '}$'
    tname = r'$\sim k^{-5/3}$'
    ax1.text(
        0.72,
        0.6,
        tname,
        color='black',
        fontsize=24,
        horizontalalignment='left',
        verticalalignment='center',
        transform=ax1.transAxes)
    ax1.tick_params(labelsize=16)
    ax1.set_xlabel(r'$kd_i$', fontdict=font, fontsize=20)
    ax1.set_ylabel(r'$E_V(k)$', fontdict=font, fontsize=20)
    ax1.set_xlim([1E-2, 3E1])
    if species is 'electron':
        ax1.set_ylim([1E-2, 0.5])
    else:
        ax1.set_xlim([1E-2, 1E0])
        ax1.set_ylim([5E9, 5E12])
    leg = ax1.legend(
        loc=1,
        prop={'size': 16},
        ncol=1,
        shadow=False,
        fancybox=False,
        frameon=False)

    fig_dir = '../img/img_power_spectrum/' + run_name + '/'
    mkdir_p(fig_dir)
    fname = fig_dir + '/ps_comp_' + species + str(ct).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=200)

    plt.close()
    # plt.show()


def calc_power_spectrum(pic_info,
                        ct,
                        species,
                        run_name,
                        xmin,
                        xmax,
                        base_dir='../../',
                        single_file=True):
    """Calculate power spectrum of compressible mode and incompressible mode

    Args:
        pic_info: namedtuple for the PIC simulation information.
        ct: current time frame.
        species: particle species
        run_name: the simulation run name
        xmin, xmax: the spatial range of the field data
        base_dir: the root directory of the run
    """
    zmin, zmax = -0.5 * pic_info.lz_di, 0.5 * pic_info.lz_di
    if single_file:
        kwargs = {
            "current_time": ct,
            "xl": xmin,
            "xr": xmax,
            "zb": zmin,
            "zt": zmax
        }
        fname = base_dir + 'data1/v' + species + 'x.gda'
        x, z, vx = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data1/v' + species + 'y.gda'
        x, z, vy = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data1/v' + species + 'z.gda'
        x, z, vz = read_2d_fields(pic_info, fname, **kwargs)
    else:
        kwargs = {
            "current_time": 0,
            "xl": xmin,
            "xr": xmax,
            "zb": zmin,
            "zt": zmax
        }
        tframe = str(fields_interval * ct)
        fname = base_dir + 'data/vex_' + tframe + '.gda'
        fname = base_dir + 'data/v' + species + 'x_' + tframe + '.gda'
        x, z, vx = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data/v' + species + 'y_' + tframe + '.gda'
        x, z, vy = read_2d_fields(pic_info, fname, **kwargs)
        fname = base_dir + 'data/v' + species + 'z_' + tframe + '.gda'
        x, z, vz = read_2d_fields(pic_info, fname, **kwargs)
    nx, = x.shape
    nz, = z.shape
    smime = math.sqrt(pic_info.mime)
    lx = np.max(x) - np.min(x)
    lz = np.max(z) - np.min(z)

    vx_k = np.fft.rfft2(vx)
    vy_k = np.fft.rfft2(vy)
    vz_k = np.fft.rfft2(vz)
    xstep = lx / nx
    kx = np.fft.fftfreq(nx, xstep)
    idx = np.argsort(kx)
    zstep = lz / nz
    kz = np.fft.fftfreq(nz, zstep)
    idz = np.argsort(kz)
    print np.min(kx), np.max(kx), np.min(kz), np.max(kz)
    print nx, nz

    kxs, kzs = np.meshgrid(kx[:nx // 2 + 1], kz)
    k = np.sqrt(kxs * kxs + kzs * kzs)

    vkpara = div0(vx_k * kxs + vz_k * kzs, k)
    vkperp_x = div0(-vy_k * kzs, k)
    vkperp_y = div0(vx_k * kzs - vz_k * kxs, k)
    vkperp_z = div0(vy_k * kxs, k)

    v2_k = np.absolute(vx_k)**2 + np.absolute(vy_k)**2 + np.absolute(vz_k)**2
    v2_kpara = np.absolute(vkpara)**2
    v2_kperp = np.absolute(vkperp_x)**2 + np.absolute(vkperp_y)**2 + \
               np.absolute(vkperp_z)**2

    kxs, kzs = np.meshgrid(kx[:nx // 2 + 1], kz)
    ks = np.sqrt(kxs * kxs + kzs * kzs)
    kmin, kmax = np.min(ks), np.max(ks)
    kmin = 1E-2
    kmin_log = math.log10(kmin)
    kmax_log = math.log10(kmax)
    # kbins = np.linspace(kmin, kmax, 256, endpoint=True)
    kbins = 10**np.linspace(kmin_log, kmax_log, 39, endpoint=True)
    ps, kbins_edges = np.histogram(ks, bins=kbins, weights=v2_k * ks)
    ps_para, kbins_edges = np.histogram(ks, bins=kbins, weights=v2_kpara * ks)
    ps_perp, kbins_edges = np.histogram(ks, bins=kbins, weights=v2_kperp * ks)
    power1 = ps / np.diff(kbins_edges)
    power2 = ps_para / np.diff(kbins_edges)
    power3 = ps_perp / np.diff(kbins_edges)
    # print power1
    # print (power1 + 1E-5) / (power2 + power3 + 1E-5)
    # print (np.sum(ps)) / (np.sum(ps_para) + np.sum(ps_perp))
    # print (np.sum(ps*np.diff(kbins_edges)))
    # print (np.sum(ps_para*np.diff(kbins_edges)))
    # print (np.sum(ps_perp*np.diff(kbins_edges)))
    return (kbins_edges, power1, power2, power3)


def plot_power_spectrum_vel_comp_du(pic_info,
                                    ct,
                                    species,
                                    run_name,
                                    xs,
                                    base_dir='../../',
                                    single_file=True):
    """
    Plot the power spectrum of the compressible and incompressible modes of
    both the upstream field and downstream field

    Args:
        pic_info: namedtuple for the PIC simulation information.
        ct: current time frame.
        species: particle species
        run_name: the simulation run name
        xs: the shock position in ion inertial length
        base_dir: the root directory of the run
    """
    s1 = 1.0
    s2 = 5.0
    xmin, xmax = xs - s2, xs - s1
    kbins, pt_d, pc_d, pi_d = calc_power_spectrum(
        pic_info, ct, species, run_name, xmin, xmax, base_dir, single_file)
    xmin, xmax = xs + s1, xs + s2
    kbins, pt_u, pc_u, pi_u = calc_power_spectrum(
        pic_info, ct, species, run_name, xmin, xmax, base_dir, single_file)
    categories = ['Upstream', 'Downstream']
    w1, h1 = 0.8, 0.7
    xs, ys = 0.15, 0.8 - h1
    fig = plt.figure(figsize=[7, 6])
    ax1 = fig.add_axes([xs, ys, w1, h1])
    p1, = ax1.loglog(
        kbins[:-1], pt_d, linewidth=2, color='k', label='Down: total')
    p2, = ax1.loglog(
        kbins[:-1],
        pc_d,
        linewidth=2,
        color=colors[0],
        label='Down: compressible')
    p3, = ax1.loglog(
        kbins[:-1],
        pi_d,
        linewidth=2,
        color=colors[1],
        label='Down: incompressible')
    p4, = ax1.loglog(
        kbins[:-1],
        pt_u,
        linewidth=2,
        color='k',
        linestyle='--',
        label='Up: total')
    p5, = ax1.loglog(
        kbins[:-1],
        pc_u,
        linewidth=2,
        linestyle='--',
        color=colors[0],
        label='Up: compressible')
    p6, = ax1.loglog(
        kbins[:-1],
        pi_u,
        linewidth=2,
        linestyle='--',
        color=colors[1],
        label='Up: incompressible')
    # psm = np.argmax(ps)
    psm = 5
    pindex = -5.0 / 3
    power_k = kbins[psm:]**pindex
    shift = 12
    if species is 'electron':
        ax1.loglog(
            kbins[psm:psm + shift],
            power_k[:shift] * 0.5 / power_k[0],
            linestyle='--',
            linewidth=2,
            color='k')
    else:
        index_s = 20
        index_ps = index_s - psm
        print kbins[index_s], kbins[index_s + shift]
        ax1.loglog(
            kbins[index_s:index_s + shift],
            power_k[index_ps:shift + index_ps] * 4E8 / power_k[index_ps],
            linestyle='-.',
            linewidth=1,
            color='k')
    power_index = "{%0.1f}" % pindex
    # tname = r'$\sim k^{' + power_index + '}$'
    tname = r'$\sim k^{-5/3}$'
    ax1.text(
        0.5,
        0.8,
        tname,
        color='black',
        fontsize=24,
        horizontalalignment='left',
        verticalalignment='center',
        transform=ax1.transAxes)
    ax1.tick_params(labelsize=16)
    ax1.set_xlabel(r'$kd_i$', fontdict=font, fontsize=20)
    ax1.set_ylabel(r'$E_V(k)$', fontdict=font, fontsize=20)
    ax1.set_xlim([1E-1, 1E1])
    if species is 'electron':
        ax1.set_ylim([1E-2, 0.5])
    else:
        ax1.set_ylim([1E6, 1E9])
    leg = ax1.legend(
        bbox_to_anchor=(0., 1.02, 1., .102),
        loc=3,
        prop={'size': 16},
        ncol=2,
        mode="expand",
        borderaxespad=0.)

    fig_dir = '../img/img_power_spectrum_du/' + run_name + '/'
    mkdir_p(fig_dir)
    fname = fig_dir + '/ps_comp_' + species + str(ct).zfill(3) + '.jpg'
    fig.savefig(fname, dpi=200)

    plt.close()
    # plt.show()


if __name__ == "__main__":
    # base_dir = '/net/scratch3/xiaocanli/2D-90-Mach4-sheet4-multi/'
    # run_name = '2D-90-Mach4-sheet4-multi'
    base_dir = '/net/scratch2/guofan/for_Senbei/2D-90-Mach4-sheet6-2/'
    run_name = '2D-90-Mach4-sheet6-2'
    picinfo_fname = '../data/pic_info/pic_info_' + run_name + '.json'
    pic_info = read_data_from_json(picinfo_fname)
    ct = pic_info.ntf - 2
    # ct = 200
    cts = range(10, pic_info.ntf - 1)

    xmin, xmax = 0, pic_info.lx_di
    xmin, xmax = 0, 105
    zmin, zmax = -0.5 * pic_info.lz_di, 0.5 * pic_info.lz_di
    # kwargs = {"current_time":ct, "xl":xmin, "xr":xmax, "zb":zmin, "zt":zmax}
    # fname = base_dir + 'data1/vex.gda'
    # x, z, vel = read_2d_fields(pic_info, fname, **kwargs) 
    kwargs = {
        "current_time": 0,
        "xl": xmin,
        "xr": xmax,
        "zb": zmin,
        "zt": zmax
    }
    fields_interval = pic_info.fields_interval
    tframe = str(fields_interval * ct)
    fname = base_dir + 'data/vex_' + tframe + '.gda'
    x, z, pxx = read_2d_fields(pic_info, fname, **kwargs)
    fname = '../data/shock_pos/shock_pos_' + run_name + '.txt'
    shock_loc = np.genfromtxt(fname, dtype=np.int32)
    sloc = shock_loc[ct]
    xm = x[sloc]

    def processInput(ct):
        print ct
        sloc = shock_loc[ct]
        xm = x[sloc]
        # calc_avg_bfield(pic_info, ct, run_name, xm, base_dir)
        # calc_power_spectrum_mag(pic_info, ct, run_name, sloc, base_dir)
        # calc_power_spectrum_vel(pic_info, ct, 'e', run_name, sloc, base_dir)
        # calc_power_spectrum_vel_comp(pic_info, ct, 'i', run_name, sloc,
        #                              base_dir, single_file=False)
        plot_power_spectrum_vel_comp_du(
            pic_info, ct, 'i', run_name, xm, base_dir, single_file=False)

    num_cores = multiprocessing.cpu_count()
    # num_cores = 8
    Parallel(n_jobs=num_cores)(delayed(processInput)(ct) for ct in cts)
    # calc_power_spectrum_mag(pic_info, ct, run_name, sloc, base_dir)
    # calc_power_spectrum_vel(pic_info, ct, 'i', run_name, sloc, base_dir)
    # calc_avg_bfield(pic_info, ct, run_name, xm, base_dir)
    # plot_avg_bfiled(pic_info)
    # calc_power_spectrum_vel_comp(pic_info, ct, 'i', run_name, sloc, base_dir,
    #                              single_file=False)
    # plot_power_spectrum_vel_comp_du(pic_info, ct, 'i', run_name, xm,
    #                                 base_dir, single_file=False)
    # for ct in cts:
    #     print ct
    #     plot_power_spectrum_vel_comp_du(pic_info, ct, 'i', run_name, xm, base_dir)
