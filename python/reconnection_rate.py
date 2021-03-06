"""
Analysis procedures to calculate and plot reconnection rate
"""
import math
import os.path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import palettable
from scipy import signal

import pic_information
from contour_plots import plot_2d_contour, read_2d_fields

mpl.rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
mpl.rc('text', usetex=True)
mpl.rcParams['text.latex.preamble'] = [r"\usepackage{amsmath}"]

FONT = {'family': 'serif',
        'color': 'black',
        'weight': 'normal',
        'size': 24}


def calc_reconnection_rate(base_dir):
    """Calculate reconnection rate.

    Args:
        base_dir: the directory base.
    """
    pic_info = pic_information.get_pic_info(base_dir)
    ntf = pic_info.ntf
    phi = np.zeros(ntf)
    fname = base_dir + 'data/Ay.gda'
    for ct in range(ntf):
        kwargs = {"current_time": ct, "xl": 0, "xr": 200, "zb": -1, "zt": 1}
        x, z, Ay = read_2d_fields(pic_info, fname, **kwargs)
        nz, = z.shape
        # max_ay = np.max(np.sum(Ay[nz/2-1:nz/2+1, :], axis=0)/2)
        # min_ay = np.min(np.sum(Ay[nz/2-1:nz/2+1, :], axis=0)/2)
        max_ay = np.max(Ay[nz / 2 - 1:nz / 2 + 1, :])
        min_ay = np.min(Ay[nz / 2 - 1:nz / 2 + 1, :])
        phi[ct] = max_ay - min_ay
    nk = 3
    phi = signal.medfilt(phi, kernel_size=nk)
    dtwpe = pic_info.dtwpe
    dtwce = pic_info.dtwce
    dtwci = pic_info.dtwci
    mime = pic_info.mime
    dtf_wpe = pic_info.dt_fields * dtwpe / dtwci
    reconnection_rate = np.gradient(phi) / dtf_wpe
    b0 = pic_info.b0
    va = dtwce * math.sqrt(1.0 / mime) / dtwpe
    reconnection_rate /= b0 * va
    reconnection_rate[-1] = reconnection_rate[-2]
    tfields = pic_info.tfields

    return (tfields, reconnection_rate)


def save_reconnection_rate(tfields, reconnection_rate, fname):
    """Save the calculated reconnection rate.
    """
    if not os.path.isdir('../data/'):
        os.makedirs('../data/')
    if not os.path.isdir('../data/rate/'):
        os.makedirs('../data/rate/')
    filename = '../data/rate/' + fname
    f = open(filename, 'w')
    np.savetxt(f, (tfields, reconnection_rate))
    f.close()


def plot_reconnection_rate(base_dir):
    """Calculate and plot the reconnection rate

    Args:
        base_dir: the directory base.
    """
    tfields, reconnection_rate = calc_reconnection_rate(base_dir)
    fig = plt.figure(figsize=[7, 5])
    ax = fig.add_axes([0.18, 0.15, 0.78, 0.8])
    ax.plot(tfields, reconnection_rate, color='black', linewidth=2)
    ax.set_xlabel(r'$t\Omega_{ci}$', fontdict=FONT, fontsize=24)
    ax.set_ylabel(r'$E_R$', fontdict=FONT, fontsize=24)
    ax.tick_params(labelsize=20)
    ax.set_ylim([0, 0.12])
    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    fname = '../img/er.eps'
    fig.savefig(fname)
    plt.show()


def calc_multi_reconnection_rate():
    """Calculate reconnection rate for multiple runs
    """
    base_dir = '/net/scratch2/xiaocanli/mime25-sigma01-beta02-200-100/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime25_beta02.dat')

    base_dir = '/net/scratch2/xiaocanli/mime25-sigma033-beta006-200-100/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime25_beta007.dat')

    base_dir = '/scratch3/xiaocanli/sigma1-mime25-beta001/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime25_beta002.dat')

    base_dir = '/scratch3/xiaocanli/sigma1-mime25-beta0003-npc200/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime25_beta0007.dat')

    base_dir = '/scratch3/xiaocanli/sigma1-mime100-beta001-mustang/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime100_beta002.dat')

    base_dir = '/scratch3/xiaocanli/mime25-guide0-beta001-200-100/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime25_beta002_sigma01.dat')

    base_dir = '/scratch3/xiaocanli/mime25-guide0-beta001-200-100-sigma033/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime25_beta002_sigma033.dat')

    base_dir = '/net/scratch2/xiaocanli/mime25-sigma1-beta002-200-100-noperturb/'
    t, rate = calc_reconnection_rate(base_dir)
    save_reconnection_rate(t, rate, 'rate_mime25_beta002_noperturb.dat')


def plot_multi_reconnection_rate():
    """Calculate reconnection rate for multiple runs
    """
    path = '../data/rate/'
    fname = path + 'rate_mime25_beta002.dat'
    tf1, rate1 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta002_sigma033.dat'
    tf2, rate2 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta002_sigma01.dat'
    tf3, rate3 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta002_noperturb.dat'
    tf4, rate4 = np.genfromtxt(fname)
    fname = path + 'rate_mime100_beta002.dat'
    tf5, rate5 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta0007.dat'
    tf6, rate6 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta007.dat'
    tf7, rate7 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta02.dat'
    tf8, rate8 = np.genfromtxt(fname)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    dir = '../img/rate/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    # Compare different density
    fig = plt.figure(figsize=[7, 5])
    ax = fig.add_axes([0.16, 0.15, 0.8, 0.8])
    colors = palettable.colorbrewer.qualitative.Set1_9.mpl_colors
    ax.set_color_cycle(colors)
    ax.plot(tf6, rate6, linewidth=2, label='R6')
    ax.plot(tf8, rate8, linewidth=2, label='R8')
    # ax.plot(tf7, rate7, linewidth=2, label='R7')
    ax.set_xlabel(r'$t\Omega_{ci}$', fontdict=FONT, fontsize=24)
    ax.set_ylabel(r'$E_R$', fontdict=FONT, fontsize=24)
    ax.tick_params(labelsize=20)
    ax.set_xlim([0, 1200])
    ax.set_ylim([0, 0.12])
    ax.legend(
        loc=1,
        prop={'size': 20},
        ncol=1,
        shadow=False,
        fancybox=False,
        frameon=False)
    fname = dir + 'rate_low_density.eps'
    fig.savefig(fname)

    # Compare different temperature
    fig = plt.figure(figsize=[7, 5])
    ax = fig.add_axes([0.18, 0.15, 0.78, 0.8])
    ax.set_color_cycle(colors)
    ax.plot(tf1, rate1, linewidth=2, label='R1')
    ax.plot(tf2, rate2, linewidth=2, label='R2')
    ax.plot(tf3, rate3, linewidth=2, label='R3')
    # ax.plot(tf4, rate4, linewidth=2, label='R4')
    # ax.plot(tf5, rate5, linewidth=2, label='R5')
    ax.set_xlabel(r'$t\Omega_{ci}$', fontdict=FONT, fontsize=24)
    ax.set_ylabel(r'$E_R$', fontdict=FONT, fontsize=24)
    ax.tick_params(labelsize=20)
    ax.set_xlim([0, 1200])
    ax.set_ylim([0, 0.12])
    ax.legend(
        loc=1,
        prop={'size': 20},
        ncol=1,
        shadow=False,
        fancybox=False,
        frameon=False)
    fname = dir + 'rate_low_temp.eps'
    fig.savefig(fname)

    # Compare different mass ratio
    fig = plt.figure(figsize=[7, 5])
    ax = fig.add_axes([0.18, 0.15, 0.78, 0.8])
    ax.set_color_cycle(colors)
    ax.plot(tf1, rate1, linewidth=2, label='R1')
    ax.plot(tf5, rate5, linewidth=2, label='R5')
    ax.set_xlabel(r'$t\Omega_{ci}$', fontdict=FONT, fontsize=24)
    ax.set_ylabel(r'$E_R$', fontdict=FONT, fontsize=24)
    ax.tick_params(labelsize=20)
    ax.set_xlim([0, 1200])
    ax.set_ylim([0, 0.12])
    ax.legend(
        loc=1,
        prop={'size': 20},
        ncol=1,
        shadow=False,
        fancybox=False,
        frameon=False)
    fname = dir + 'rate_mass.eps'
    fig.savefig(fname)

    # Compare different initial condition
    fig = plt.figure(figsize=[7, 5])
    ax = fig.add_axes([0.18, 0.15, 0.78, 0.8])
    ax.set_color_cycle(colors)
    ax.plot(tf1, rate1, linewidth=2, label='R1')
    ax.plot(tf4, rate4, linewidth=2, label='R4')
    ax.set_xlabel(r'$t\Omega_{ci}$', fontdict=FONT, fontsize=24)
    ax.set_ylabel(r'$E_R$', fontdict=FONT, fontsize=24)
    ax.tick_params(labelsize=20)
    ax.set_xlim([0, 1200])
    ax.set_ylim([0, 0.12])
    ax.legend(
        loc=1,
        prop={'size': 20},
        ncol=1,
        shadow=False,
        fancybox=False,
        frameon=False)
    fname = dir + 'rate_initial.eps'
    fig.savefig(fname)

    plt.show()


def plot_reconnection_rate():
    """Calculate reconnection rate for multiple runs
    """
    path = '../data/rate/'
    fname = path + 'rate_mime25_beta002.dat'
    tf1, rate1 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta002_sigma033.dat'
    tf2, rate2 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta002_sigma01.dat'
    tf3, rate3 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta002_noperturb.dat'
    tf4, rate4 = np.genfromtxt(fname)
    fname = path + 'rate_mime100_beta002.dat'
    tf5, rate5 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta0007.dat'
    tf6, rate6 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta007.dat'
    tf7, rate7 = np.genfromtxt(fname)
    fname = path + 'rate_mime25_beta02.dat'
    tf8, rate8 = np.genfromtxt(fname)

    if not os.path.isdir('../img/'):
        os.makedirs('../img/')
    dir = '../img/rate/'
    if not os.path.isdir(dir):
        os.makedirs(dir)
    colors = palettable.colorbrewer.qualitative.Set1_9.mpl_colors

    # Compare different temperature
    fig = plt.figure(figsize=[7, 5])
    w1, h1 = 0.82, 0.4
    xs, ys = 0.13, 0.97 - h1
    ax = fig.add_axes([xs, ys, w1, h1])
    ax.set_color_cycle(colors)
    ax.plot(tf1, rate1, linewidth=2, label='R1')
    ax.plot(tf3, rate3, linewidth=2, label='R3')
    ax.plot(tf5, rate5, linewidth=2, label='R5')
    ax.set_ylabel(r'$E_R$', fontdict=FONT, fontsize=20)
    ax.tick_params(axis='x', labelbottom='off')
    ax.tick_params(labelsize=16)
    ax.set_xlim([0, 1200])
    ax.set_ylim([0, 0.12])
    leg = ax.legend(
        loc=1,
        prop={'size': 20},
        ncol=1,
        shadow=False,
        fancybox=False,
        frameon=False)
    for color, text in zip(colors[0:3], leg.get_texts()):
        text.set_color(color)

    ys -= h1 + 0.05
    ax1 = fig.add_axes([xs, ys, w1, h1])
    ax1.set_color_cycle(colors)
    ax1.plot(tf6, rate6, linewidth=2, label='R6', color=colors[3])
    ax1.plot(tf8, rate8, linewidth=2, label='R8', color=colors[4])
    ax1.set_xlabel(r'$t\Omega_{ci}$', fontdict=FONT, fontsize=20)
    ax1.set_ylabel(r'$E_R$', fontdict=FONT, fontsize=20)
    ax1.tick_params(labelsize=16)
    ax1.set_xlim([0, 1200])
    ax1.set_ylim([0, 0.12])
    leg1 = ax1.legend(
        loc=1,
        prop={'size': 20},
        ncol=1,
        shadow=False,
        fancybox=False,
        frameon=False)
    for color, text in zip(colors[3:5], leg1.get_texts()):
        text.set_color(color)
    fname = dir + 'rec_rate.eps'
    fig.savefig(fname)

    plt.show()


if __name__ == "__main__":
    # plot_reconnection_rate('../../')
    # calc_multi_reconnection_rate()
    # plot_multi_reconnection_rate()
    plot_reconnection_rate()
