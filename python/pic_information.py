"""
Read particle-in-cell (VPIC) simulation information.
"""
import numpy as np
import math
import os.path
import struct
import collections
import cPickle as pickle
import simplejson as json
from serialize_json import data_to_json, json_to_data
from os import listdir
from os.path import isfile, join

def get_pic_info(base_directory):
    """Get particle-in-cell simulation information.

    Args:
        base_directory: the base directory for different runs.
    """
    pic_initial_info = read_pic_info(base_directory)
    dtwpe = pic_initial_info.dtwpe
    dtwce = pic_initial_info.dtwce
    dtwci = pic_initial_info.dtwci
    dtwpi = dtwpe / math.sqrt(pic_initial_info.mime)
    ntf = get_fields_frames(base_directory)
    energy_interval = pic_initial_info.energy_interval
    fields_interval, particle_interval = \
            get_output_intervals(dtwpe, dtwce, dtwpi, dtwci, base_directory)
    dt_fields = fields_interval * dtwci
    dt_particles = particle_interval * dtwci
    ntp = ntf / (particle_interval/fields_interval)
    tparticles = np.arange(ntp) * dt_particles
    tfields = np.arange(ntf) * dt_fields
    dt_energy = energy_interval * dtwci
    dte_wpe = dt_energy * dtwpe / dtwci
    pic_ene = read_pic_energies(dt_energy, dte_wpe, base_directory)
    pic_times = collections.namedtuple("pic_times", 
            ['ntf', 'dt_fields', 'tfields', 'ntp', 'dt_particles', 
                'tparticles', 'dt_energy', 'fields_interval', 'particle_interval'])
    pic_times_info = pic_times(ntf=ntf, dt_fields=dt_fields,
            dt_particles=dt_particles, tfields=tfields, dt_energy=dt_energy,
            ntp=ntp, tparticles=tparticles, fields_interval=fields_interval,
            particle_interval=particle_interval)
    pic_topology = get_pic_topology(base_directory)
    pic_information = collections.namedtuple("pic_information", 
            pic_initial_info._fields + pic_times_info._fields +
            pic_ene._fields + pic_topology._fields)
    pic_info = pic_information(*(pic_initial_info + pic_times_info +
        pic_ene + pic_topology))
    return pic_info


def read_pic_energies(dte_wci, dte_wpe, base_directory):
    """Read particle-in-cell simulation energies.

    Args:
        dte_wci: the time interval for energies diagnostics (in 1/wci).
        dte_wpe: the time interval for energies diagnostics (in 1/wpe).
        base_directory: the base directory for different runs.
    """
    fname = base_directory + '/energies'
    try:
        f = open(fname, 'r')
    except IOError:
        print 'cannot open ', fname
        return
    else:
        content = np.genfromtxt(f, skip_header=3)
        f.close()
        nte, nvar = content.shape
        tenergy = np.arange(nte) * dte_wci
        ene_ex = content[:,1]
        ene_ey = content[:,2]
        ene_ez = content[:,3]
        ene_bx = content[:,4]
        ene_by = content[:,5]
        ene_bz = content[:,6]
        kene_i = content[:,7] # kinetic energy for ions
        kene_e = content[:,8]
        ene_electric = ene_ex + ene_ey + ene_ez
        ene_magnetic = ene_bx + ene_by + ene_bz
        dene_ex = np.gradient(ene_ex) / dte_wpe
        dene_ey = np.gradient(ene_ey) / dte_wpe
        dene_ez = np.gradient(ene_ez) / dte_wpe
        dene_bx = np.gradient(ene_bx) / dte_wpe
        dene_by = np.gradient(ene_by) / dte_wpe
        dene_bz = np.gradient(ene_bz) / dte_wpe
        dene_electric = np.gradient(ene_electric) / dte_wpe
        dene_magnetic = np.gradient(ene_magnetic) / dte_wpe
        dkene_i = np.gradient(kene_i) / dte_wpe
        dkene_e = np.gradient(kene_e) / dte_wpe
        pic_energies = collections.namedtuple('pic_energies',
                ['nte', 'tenergy', 'ene_ex', 'ene_ey', 'ene_ez', 'ene_bx',
                    'ene_by', 'ene_bz','kene_i', 'kene_e', 'ene_electric',
                    'ene_magnetic', 'dene_ex', 'dene_ey', 'dene_ez', 'dene_bx',
                    'dene_by', 'dene_bz','dkene_i', 'dkene_e', 'dene_electric',
                    'dene_magnetic'])
        pic_ene = pic_energies(nte=nte, tenergy=tenergy, ene_ex=ene_ex,
                ene_ey=ene_ey, ene_ez=ene_ez, ene_bx=ene_bx, ene_by=ene_by,
                ene_bz=ene_bz, kene_i=kene_i, kene_e=kene_e,
                ene_electric=ene_electric, ene_magnetic=ene_magnetic, 
                dene_ex=dene_ex, dene_ey=dene_ey, dene_ez=dene_ez,
                dene_bx=dene_bx, dene_by=dene_by, dene_bz=dene_bz,
                dkene_i=dkene_i, dkene_e=dkene_e,
                dene_electric=dene_electric, dene_magnetic=dene_magnetic)
        return pic_ene


def get_fields_frames(base_directory):
    """Get the total number of time frames for fields.

    Args:
        base_directory: the base directory for different runs.
    Returns:
        ntf: the total number of output time frames for fields.
    """
    pic_initial_info = read_pic_info(base_directory)
    nx = pic_initial_info.nx
    ny = pic_initial_info.ny
    nz = pic_initial_info.nz
    fname = base_directory + '/data/ex.gda'
    fname_fields = base_directory + '/fields/T.1'
    fname_bx = base_directory + '/data/bx_0.gda'
    if (os.path.isfile(fname_bx)):
        current_time = 1
        is_exist = False
        while (not is_exist):
            current_time += 1
            fname = base_directory + '/data/bx_' + str(current_time) + '.gda'
            is_exist = os.path.isfile(fname)
        fields_interval = current_time
        ntf = 1
        is_exist = True
        while (is_exist):
            ntf += 1
            current_time += fields_interval
            fname = base_directory + '/data/bx_' + str(current_time) + '.gda'
            is_exist = os.path.isfile(fname)
    elif (os.path.isfile(fname)):
        file_size = os.path.getsize(fname)
        ntf = int(file_size/(nx*ny*nz*4))
    elif (os.path.isdir(fname_fields)):
        current_time = 1
        is_exist = False
        while (not is_exist):
            current_time += 1
            fname = base_directory + '/fields/T.' + str(current_time)
            is_exist = os.path.isdir(fname)
        fields_interval = current_time
        ntf = 1
        is_exist = True
        while (is_exist):
            ntf += 1
            current_time += fields_interval
            fname = base_directory + '/fields/T.' + str(current_time)
            is_exist = os.path.isdir(fname)
    else:
        print 'Cannot find the files to calculate the total frames of fields.'
        return
    return ntf


def get_main_source_filename(base_directory):
    """Get the source file name.

    Get the configuration source file name for the PIC simulation.

    Args:
        base_directory: the base directory for different runs.
    """
    fname = base_directory + '/Makefile'
    try:
        f = open(fname, 'r')
    except IOError:
        print 'cannot open ', fname
    else:
        content = f.readlines()
        f.close()
        nlines = len(content)
        current_line = 0
        while not 'vpic' in content[current_line]: current_line += 1
        single_line = content[current_line]
        line_splits = single_line.split(".op")
        word_splits = line_splits[1].split(" ")

    filename = word_splits[1]
    fname = base_directory + '/' + filename[:-1]
    return fname


def get_output_intervals(dtwpe, dtwce, dtwpi, dtwci, base_directory):
    """
    Get output intervals from the main configuration file for current PIC
    simulation.
    
    Args:
        dtwpe: the time step in 1/wpe.
        dtwce: the time step in 1/wce.
        dtwpi: the time step in 1/wpi.
        dtwci: the time step in 1/wci.
        base_directory: the base directory for different runs.
    """
    fname = get_main_source_filename(base_directory)
    try:
        f = open(fname, 'r')
    except IOError:
        print 'cannot open ', fname
    else:
        content = f.readlines()
        f.close()
        nlines = len(content)
        current_line = 0
        cond1 = not 'int interval = ' in content[current_line] 
        cond2 = '//' in content[current_line]  # commented out
        while cond1 or cond2:
            current_line += 1
            cond1 = not 'int interval = ' in content[current_line] 
            cond2 = '//' in content[current_line]  # commented out
        if not '(' in content[current_line]:
            single_line = content[current_line]
            if '*' in content[current_line]:
                line_splits = single_line.split('*')
                word_splits = line_splits[0].split('=')
                time_ratio = float(word_splits[1])
            else:
                line_splits = single_line.split('=')
                time_ratio = 1.0
            word_splits = line_splits[1].split(";")
            word = 'int ' + word_splits[0] + ' = '
            cline = current_line
            # go back to the number for word_splits[0]
            cond1 = not word in content[current_line] 
            cond2 = '//' in content[current_line]  # commented out
            while cond1 or cond2:
                current_line -= 1
                cond1 = not word in content[current_line]
                cond2 = '//' in content[current_line]  # commented out
            interval = get_time_interval(content[current_line], dtwpe, dtwce,
                    dtwpi, dtwci)
            interval = int(interval * time_ratio)
        else:
            interval = get_time_interval(content[current_line], dtwpe, dtwce,
                    dtwpi, dtwci)
        
        fields_interval = interval

        while not 'int eparticle_interval' in content[current_line]: 
            current_line += 1
        single_line = content[current_line]
        line_splits = single_line.split("=")
        word_splits = line_splits[1].split("*")
        particle_interval = int(word_splits[0]) * interval

    return (fields_interval, particle_interval)

def get_time_interval(line, dtwpe, dtwce, dtwpi, dtwci):
    """Get time interval from a line
    
    The line is in the form: int *** = int(5.0/***);

    Args:
        line: one single line
        dtwpe: the time step in 1/wpe.
        dtwce: the time step in 1/wce.
        dtwpi: the time step in 1/wpi.
        dtwci: the time step in 1/wci.
    """
    line_splits = line.split("(")
    word_splits = line_splits[1].split("/")
    interval = float(word_splits[0])
    word2_splits = line_splits[2].split("*")
    dt = 0.0
    if word2_splits[0] == "wpe":
        dt = dtwpe
    elif word2_splits[0] == "wce":
        dt = dtwce
    elif word2_splits[0] == "wpi":
        dt = dtwpi
    elif word2_splits[0] == "wci":
        dt = dtwci

    interval = int(interval/dt)
    return interval

def read_pic_info(base_directory):
    """Read particle-in-cell simulation information.
    
    Args:
        pic_info: a namedtuple for PIC initial information.
    """
    fname = base_directory + '/info'
    with open(fname) as f:
        content = f.readlines()
    f.close()
    nlines = len(content)
    current_line = 0
    mime, current_line = get_variable_value('mi/me', current_line, content)
    lx, current_line = get_variable_value('Lx/di', current_line, content)
    ly, current_line = get_variable_value('Ly/di', current_line, content)
    lz, current_line = get_variable_value('Lz/di', current_line, content)
    nx, current_line = get_variable_value('nx', current_line, content)
    ny, current_line = get_variable_value('ny', current_line, content)
    nz, current_line = get_variable_value('nz', current_line, content)
    nx = int(nx)
    ny = int(ny)
    nz = int(nz)
    nppc, current_line = get_variable_value('nppc', current_line, content)
    b0, current_line = get_variable_value('b0', current_line, content)
    dtwpe, current_line = get_variable_value('dt*wpe', current_line, content)
    dtwce, current_line = get_variable_value('dt*wce', current_line, content)
    dtwci, current_line = get_variable_value('dt*wci', current_line, content)
    while not 'energies_interval' in content[current_line]: current_line += 1
    single_line = content[current_line]
    line_splits = single_line.split(":")
    energy_interval = float(line_splits[1])
    dxde, current_line = get_variable_value('dx/de', current_line, content)
    dyde, current_line = get_variable_value('dy/de', current_line, content)
    dzde, current_line = get_variable_value('dz/de', current_line, content)
    dxdi = dxde / math.sqrt(mime)
    dydi = dyde / math.sqrt(mime)
    dzdi = dzde / math.sqrt(mime)
    x = np.arange(nx)*dxdi
    y = (np.arange(ny)-ny/2.0+0.5)*dydi
    z = (np.arange(nz)-nz/2.0+0.5)*dzdi
    vthi, current_line = get_variable_value('vthi/c', current_line, content)
    vthe, current_line = get_variable_value('vthe/c', current_line, content)

    pic_init_info = collections.namedtuple('pic_init_info',
            ['mime', 'lx_di', 'ly_di', 'lz_di', 'nx', 'ny', 'nz',
                'dx_di', 'dy_di', 'dz_di', 'x_di', 'y_di', 'z_di', 'nppc', 'b0',
                'dtwpe', 'dtwce', 'dtwci', 'energy_interval', 'vthi', 'vthe'])
    pic_info = pic_init_info(mime=mime, lx_di=lx, ly_di=ly, lz_di=lz,
            nx=nx, ny=ny, nz=nz, dx_di=dxdi, dy_di=dydi, dz_di=dzdi, 
            x_di=x, y_di=y, z_di=z, nppc=nppc, b0=b0, dtwpe=dtwpe, dtwce=dtwce,
            dtwci=dtwci, energy_interval=energy_interval, vthi=vthi, vthe=vthe)
    return pic_info


def get_variable_value(variable_name, current_line, content):
    """
    Get the value of one variable from the content of the information file.

    Args:
        variable_name: the variable name.
        current_line: current line number.
        content: the content of the information file.
    Returns:
        variable_value: the value of the variable.
        line_number: current line number after the operations.
    """
    line_number = current_line
    while not variable_name in content[line_number]: line_number += 1
    single_line = content[line_number]
    line_splits = single_line.split("=")
    variable_value = float(line_splits[1])
    return (variable_value, line_number)


def get_pic_topology(base_directory):
    """Get the PIC simulation topology

    Args:
        base_directory: the base directory for different runs.
    """
    fname = get_main_source_filename(base_directory)
    try:
        f = open(fname, 'r')
    except IOError:
        print 'cannot open ', fname
    else:
        content = f.readlines()
        f.close()
        nlines = len(content)
        current_line = 0
        while not 'double topology_x =' in content[current_line]:
            current_line += 1
        single_line = content[current_line]
        line_splits = single_line.split("=")
        word_splits = line_splits[1].split(";")
        topology_x = int(word_splits[0])
        current_line += 1
        single_line = content[current_line]
        line_splits = single_line.split("=")
        word_splits = line_splits[1].split(";")
        topology_y = int(word_splits[0])
        current_line += 1
        single_line = content[current_line]
        line_splits = single_line.split("=")
        word_splits = line_splits[1].split(";")
        topology_z = int(word_splits[0])
    pic_topology = collections.namedtuple('pic_topology',
            ['topology_x', 'topology_y', 'topology_z'])
    pic_topo = pic_topology(topology_x = topology_x,
            topology_y = topology_y, topology_z = topology_z)
    return pic_topo


def save_pic_info_json():
    """Save pic_info for different runs as json format
    """
    if not os.path.isdir('../data/'):
        os.makedirs('../data/')
    dir = '../data/pic_info/'
    if not os.path.isdir(dir):
        os.makedirs(dir)

    base_dir = '/net/scratch2/xiaocanli/mime25-sigma01-beta02-200-100/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime25_beta02.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)

    base_dir = '/net/scratch2/xiaocanli/mime25-sigma033-beta006-200-100/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime25_beta007.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)

    base_dir = '/scratch3/xiaocanli/sigma1-mime25-beta001/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime25_beta002.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)

    base_dir = '/scratch3/xiaocanli/sigma1-mime25-beta0003-npc200/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime25_beta0007.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)

    base_dir = '/scratch3/xiaocanli/sigma1-mime100-beta001-mustang/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime100_beta002.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)

    base_dir = '/scratch3/xiaocanli/mime25-guide0-beta001-200-100/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime25_beta002_sigma01.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)

    base_dir = '/scratch3/xiaocanli/mime25-guide0-beta001-200-100-sigma033/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime25_beta002_sigma033.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)

    base_dir = '/net/scratch2/xiaocanli/mime25-sigma1-beta002-200-100-noperturb/'
    pic_info = get_pic_info(base_dir)
    pic_info_json = data_to_json(pic_info)
    fname = dir + 'pic_info_mime25_beta002_noperturb.json'
    with open(fname, 'w') as f:
        json.dump(pic_info_json, f)


def list_pic_info_dir(filepath):
    """List all of the json files of the PIC information

    Args:
        filepath: the filepath saving the json files.

    Returns:
        pic_infos: the list of filenames.
    """
    pic_infos = [f for f in listdir(filepath) if isfile(join(filepath,f))]
    return pic_infos


if __name__ == "__main__":
    # base_directory = '../../'
    # pic_info = get_pic_info(base_directory)
    save_pic_info_json()
    # list_pic_info_dir('../data/pic_info/')
