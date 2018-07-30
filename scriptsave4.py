import os
import math
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as sig
from pulson440_formats import CONFIG_MSG_FORMAT
from pulson440_constants import SPEED_OF_LIGHT, T_BIN, DN_BIN
import pandas
import timeit
import random
from numpy import *
from matplotlib.pyplot import *

DT_0 = 10
pulse_data = 'day2_people'
platform_position_data = '5vertlineallen.csv'
given_object = 'triangle.csv'

size = 420
manual_adjust = 50
eyeballing_time_start = 40

def read_config_data(file_handle, legacy=False):
    """
    Read in configuration data based on platform.
    """
    config = dict.fromkeys(CONFIG_MSG_FORMAT.keys())
    
    if legacy:
        config_msg = file_handle.read(44)
        config['node_id'] = np.frombuffer(config_msg[4:8], dtype='>u4')[0]
        config['scan_start'] = np.frombuffer(config_msg[8:12], dtype='>i4')[0]
        config['scan_stop'] = np.frombuffer(config_msg[12:16], dtype='>i4')[0]
        config['scan_res'] = np.frombuffer(config_msg[16:18], dtype='>u2')[0]
        config['pii'] = np.frombuffer(config_msg[18:20], dtype='>u2')[0]
        config['ant_mode'] = np.uint16(config_msg[32])
        config['tx_gain_ind'] = np.uint16(config_msg[33])
        config['code_channel'] = np.uint16(config_msg[34])
        config['persist_flag'] = np.uint16(config_msg[35])
        
    else:
        config_msg = file_handle.read(32)
        byte_counter = 0
        for config_field in CONFIG_MSG_FORMAT.keys():
            num_bytes = CONFIG_MSG_FORMAT[config_field].itemsize
            config_data = config_msg[byte_counter:(byte_counter + num_bytes)]
            config[config_field] = np.frombuffer(config_data,
                  dtype=CONFIG_MSG_FORMAT[config_field])[0]
            config[config_field] = config[config_field].byteswap()
            byte_counter += num_bytes
            
    return config

def unpack(file, legacy=False):
    """
    Unpacks PulsOn 440 radar data from input file
    """
    with open(file, 'rb') as f:
        config = read_config_data(f, legacy)
        
        scan_start_time = float(config['scan_start'])
        scan_end_time = float(config['scan_stop'])
        num_range_bins = DN_BIN * math.ceil((scan_end_time - scan_start_time) /
                                           (T_BIN * 1000 * DN_BIN))
        num_packets_per_scan = math.ceil(num_range_bins / 350)
        start_range = SPEED_OF_LIGHT * ((scan_start_time * 1e-12) - DT_0 * 1e-9) / 2
        drange_bins = SPEED_OF_LIGHT * T_BIN * 1e-9 / 2
        range_bins = start_range + drange_bins * np.arange(0, num_range_bins, 1)
        
        data = dict()
        data= {'scan_data': [],
               'time_stamp': [],
               'packet_ind': [],
               'packet_pulse_ind': [],
               'range_bins': range_bins}
        single_scan_data = []
        packet_count = 0
        pulse_count = 0
        
        while True:
            packet = f.read(1452)
            if len(packet) < 1452:
                break            
            packet_count += 1
            
            data['packet_ind'].append(np.frombuffer(packet[48:50], dtype='u2'))
            
            if packet_count % num_packets_per_scan == 0:
                num_samples = num_range_bins % 350
                packet_data = np.frombuffer(packet[52:(52 + 4 * num_samples)], 
                                                   dtype='>i4')
                single_scan_data.append(packet_data)
                data['scan_data'].append(np.concatenate(single_scan_data))
                data['time_stamp'].append(np.frombuffer(packet[8:12], 
                    dtype='>u4'))
                single_scan_data = []
                pulse_count += 1
            else:
                num_samples = 350
                packet_data = np.frombuffer(packet[52:(52 + 4 * num_samples)], 
                                                   dtype='>i4')
                single_scan_data.append(packet_data)
            
        if single_scan_data:
            single_scan_data = np.concatenate(single_scan_data)
            num_pad = data['scan_data'][0].size - single_scan_data.size
            single_scan_data = np.pad(single_scan_data, (0, num_pad), 
                                      'constant', constant_values=0)
            data['scan_data'].append(single_scan_data)
                
        data['scan_data'] = np.stack(data['scan_data'])
        
        data['time_stamp']

        return data

def extract_complex_pulse():
    data = unpack(pulse_data)
    
    scan_data2 = data['scan_data']

    complex_pulse = sig.hilbert(scan_data2)
    return complex_pulse

def extract_time_stamp():
    data = unpack(pulse_data)

    time_stamp2 = data['time_stamp']
    return time_stamp2

def extract_range_bins():
    data = unpack(pulse_data)
    
    range_bins2 = data['range_bins']
    return range_bins2

def extract_platform_position():
    array = list()
    new_array = list()
    position_array = list()
    final_result = list()
    data = pandas.read_csv(platform_position_data, skiprows=2, low_memory = False)
    for elements in data:
        if "Rigid Body" in elements and "Marker" not in elements:
            array.append(elements)
    for contents in array:
        for col in data[contents]:
            if type(col) == str and "Position" in col:
                new_array.append(contents)
    for contents2 in new_array:
        position_array.append(data[contents2][4:].values)
    position_array = np.array(position_array).astype(np.float)
    for contents3 in range(len(position_array[0])):
        mini_array = list()
        for contents4 in range(len(position_array)):
            mini_array.append(position_array[contents4][contents3])
        final_result.append(np.array(mini_array))
    final_result = np.array(final_result)
    return final_result

def extract_given_object():
    array = list()
    new_array = list()
    position_array = list()
    final_result = list()
    data = pandas.read_csv(given_object, skiprows=2, low_memory = False)
    for elements in data:
        if "Rigid Body" in elements and "Marker" not in elements:
            array.append(elements)
    for contents in array:
        for col in data[contents]:
            if type(col) == str and "Position" in col:
                new_array.append(contents)
    for contents2 in new_array:
        position_array.append(data[contents2][4:].values)
    position_array = np.array(position_array).astype(np.float)
    for contents3 in range(len(position_array[0])):
        mini_array = list()
        for contents4 in range(len(position_array)):
            mini_array.append(position_array[contents4][contents3])
        final_result.append(np.array(mini_array))
    final_result = np.array(final_result)
    return final_result

def extract_time_stamp2():
    array = list()
    time_array = list()
    data = pandas.read_csv(platform_position_data, skiprows=6)
    for elements in data:
        if "Time" in elements:
            array.append(elements)
    for contents2 in array:
        time_array.append(data[contents2][0:].values)
    time_array = np.array(time_array).astype(np.float)
    return time_array

def get_start_time_platform():
    pltpos = extract_platform_position()
    mini = 2 ** 63 -1
    maxi = -2 ** 63 -1
    for n in range(1000):
        if pltpos[n][2] > maxi:
            maxi = pltpos[n][2] 
        if pltpos[n][2] < mini:
            mini = pltpos[n][2]
    start_time = None
    n = 0
    while start_time == None:
         if abs(pltpos[n+100][2] - pltpos[n][2]) > abs(mini - maxi):
             start_time = n+100
         n += 1 
    return start_time

def get_parabola(): # dont use
    cxpls = extract_complex_pulse()
    abscxpls = abs(cxpls)
    distance = list()
    x = list()
    interm = get_start_time_highest_intensity()[1]
    adjust = get_start_time_highest_intensity()[0]
    for n in range(len(abscxpls)):
        distance.append((math.sqrt((interm) ** 2 + (len(abscxpls) / 2 - n) ** 2)))
    adjust_refine = adjust - len(abscxpls) /2
    for n in range(len(abscxpls)):
        x.append(n + adjust_refine-manual_adjust)
    return [x,distance]
    
def get_start_time_pulses(): #use to find start of line-->curve-->line
    cxpls = extract_complex_pulse()
    abscxpls = abs(cxpls)
    mini = 2 ** 63 -1
    maxi = -2 ** 63 -1
    for n in range(40):
        if abscxpls[n][0] > maxi:
            maxi = abscxpls[n][0] 
        if abscxpls[n][0] < mini:
            mini = abscxpls[n][0]
    interm = None
    n = 0
    while interm == None:
         if abs(abscxpls[n+5][2] - abscxpls[n][2]) > abs(mini - maxi):
             interm = n+5
         n += 1
    return interm

def intersect(): #use to graph pulse data and parabola 
    cxpls = extract_complex_pulse()
    abscxpls = abs(cxpls)
    plt.imshow(abscxpls)
    x = get_parabola()[0]
    distance = get_parabola()[1]
    plt.plot(distance,x,'r--')

def get_start_time_highest_intensity(): #dont use
    cxpls = extract_complex_pulse()
    abscxpls = abs(cxpls)
    maxi = -2 ** 63 -1
    for n in range(len(abscxpls[0])):
        for no in range(len(abscxpls)):
            if abscxpls[no][n] > maxi:
                maxi  = abscxpls[no][n]
    for n in range(len(abscxpls[0])):
        for no in range(len(abscxpls)):
            if abscxpls[no][n] == maxi:
                return [no,n]
    
def average_5_pixels(x,y,abscxpls): #dont use
    return (abscxpls[x-2][y] + abscxpls[x-1][y] + abscxpls[x][y] + abscxpls[x+1][y] + abscxpls[x+2][y]) / 5.0

def get_range(radar_xpos, radar_ypos, radar_zpos, img_x, img_y, img_z):
    return math.sqrt((radar_xpos - img_x)**2 + (radar_ypos - img_y)**2 + (radar_zpos - img_z)**2)

def combine_all_arrays():
    pickle_file = list()
    x = time_align_interpolation()
    pickle_file.append(x[1])
    pickle_file.append(x[0])
    pickle_file.append(extract_range_bins())
    pickle_file = np.array(pickle_file)
    return pickle_file

def create_SAR_image(pickle_file):
    start = timeit.default_timer()

    radar_positions = pickle_file[0]
    pulses = pickle_file[1]
    range_bins = pickle_file[2]
    
    radar_x = []
    for position in radar_positions:
        radar_x.append(position[2])
    radar_y = []
    for position in radar_positions:
        radar_y.append(position[0])
    radar_z = []
    for position in radar_positions:
        radar_z.append(position[1])
        
    plt.plot(radar_x)
    plt.show()
    plt.plot(radar_y)
    plt.show()
    plt.plot(radar_z)
    
    tempy = int(range_bins[len(range_bins)-1] - range_bins[0])/2
    tempx = -int(get_range(radar_x[0], radar_y[0], radar_z[0], radar_x[len(radar_x)-1], radar_y[len(radar_y)-1], radar_z[len(radar_z)-1]))/2
    size = abs(int(tempx*tempy*40))
    pixel_values = np.zeros((int(abs(size*tempx/tempy)),size),dtype = complex)
    pixel_values2 = np.zeros((int(abs(size*tempx/tempy)),size))
    y = int(range_bins[len(range_bins)-1] - range_bins[0])/2
    for ii in range(int(abs(size*tempx/tempy))):
        x = -int(get_range(radar_x[0], radar_y[0], radar_z[0], radar_x[len(radar_x)-1], radar_y[len(radar_y)-1], radar_z[len(radar_z)-1]))/2
        for jj in range(int(abs(size))):
            for kk in range(len(radar_x)):
                z = 0
                distance = get_range(radar_x[kk], radar_y[kk], radar_z[kk], x, y, z)
                ratio = (distance % ((range_bins[1]-range_bins[0])/2)) / ((range_bins[1]-range_bins[0])/2)
                index = math.floor(((range_bins[1]-range_bins[0])/2))
                pixel_values[ii][jj] += (pulses[kk][index]*(1-ratio) + pulses[kk][index+1]*(ratio))
            pixel_values[ii][jj] = np.abs(pixel_values[ii][jj])
            x = x + (abs(tempx)*2)/(size*x/y)
        y = y - (abs(tempy)*2)/size
    for elements in range(len(pixel_values)):
        for elements2 in range(len(pixel_values[0])):
            pixel_values2[elements,elements2] = pixel_values[elements,elements2].real
    plt.imshow(pixel_values2)

    end = timeit.default_timer()
    print(end-start)
    
def show_image_determine_start_time():
    intersect()
    
def time_align_interpolation():
    cxpls = extract_complex_pulse()
    abscxpls = abs(cxpls)
    pltpos = extract_platform_position()
    strplat = get_start_time_platform()
    strrad = eyeballing_time_start
    stamprad = list(map(float,extract_time_stamp()))
    stamppla = extract_time_stamp2()
    r = np.array(stamprad).astype(float)
    p = np.array(stamppla).astype(float)
    cutcxpls = abscxpls[strrad:][:]
    cutpltpos = pltpos[strplat:][:]
    freqr = 1/(float(r[1]) - float(r[0])) * 1000
    freqp = 1/(p[0][1] - p[0][0]) 
    divide = float(freqp / freqr)
    points = list()
    points.append(pltpos[strplat])
    n = 0
    index = None
    for elements in range(len(cutcxpls)):
        floor = math.floor(divide * elements)
        if floor + 1 < len(cutpltpos):
            if divide * elements - floor > 0.5:
                points.append(cutpltpos[floor+1])
            else:
                points.append(cutpltpos[floor])
            '''
            slope = (cutpltpos[floor+1] - cutpltpos[floor]).reshape(3,1)
            vector_p = slope * (divide * elements) + cutpltpos[floor].reshape(3,1)
            points.append(vector_p.reshape(1,3)[0])
            '''
        else:
            if index == None:
                index = n
        n += 1
    
    cxpls = cxpls[strrad:][:]
    if index != None:
        cxpls = cxpls[:index+1][:]
    return [cxpls,points]


#create_SAR_image(combine_all_arrays())
#show_image_determine_start_time()
#time_align_interpolation()
extract_given_object()