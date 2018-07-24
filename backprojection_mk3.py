'''
backprojection_mk3.py
@author   Kiryu Sakakibara, Allen Wang, Charles Cheng, Ethan Fang
@since    7/16/2018
Using the data of signal pulses and UAS coordinates, forms an image using back-projection
'''
import matplotlib.pyplot as plt
import pickle
import numpy as np
import math
import timeit
import argparse
import os
from pulson440_constants import SPEED_OF_LIGHT

start = timeit.default_timer()

f = open(r"D:\Desktop\UAV-SAR\mandrill_no_aliasing_data.pkl", "rb")
data = pickle.load(f)

size = 500 # number of pixels per axis of the image, change to alter resolution


# Returns the distance(range) between the radar and a specific location in the 3D cartesian coordinate plane

def get_range(radar_xpos, radar_ypos, radar_zpos, img_x, img_y):
    return math.sqrt((radar_xpos - img_x)**2 + (radar_ypos - img_y)**2 + (radar_zpos)**2)

'''
Plots a picture that illustrates the edges of the source image
@param   arr   the 2D array or list of lists that contains the sum magnitude of pulses
@param   diff  the index that dictates how much contrast the algorithm is looking for
'''
def edge_detection(arr, diff):
    ED = np.zeros((len(arr),len(arr[0]),3))
    for row in range(len(arr)):
        for col in range(len(arr[0])):
           # if col is not len(arr[0]) - 1:
            if (col < len(arr[0]) - 1 and np.absolute(arr[row][col]-arr[row][col+1]) > diff) or (row < len(arr) - 4 and np.absolute(arr[row][col]-arr[row+4][col]) > diff*4):
                ED[row,col,0] = 255
                ED[row,col,1] = 255
                ED[row,col,2] = 255
            else:
                ED[row,col,0] = 1
                ED[row,col,1] = 1
                ED[row,col,2] = 1
    return ED

'''
x and y represent pixel coordinate. Difference between start and end x and start and end y
must be less than size, and start x/y must be greater or equal to zero.
def partImage returns a 2d array of magnitudes from a range of pixels defined
by the parameters
'''
def partImage(start_x, start_y, end_x, end_y):
    xDiff = np.abs(end_x - start_x)
    yDiff = (end_y - start_y)
    pulseArr = list(list(0+0j for ii in np.arange(0, xDiff)) for jj in np.arange(0, yDiff))
    magArr = list(list(0+0j for ii in np.arange(0, xDiff)) for jj in np.arange(0, yDiff))
    y = 2.5 - (5.0/size)*start_y
    for ii in np.arange(0, yDiff):
        x = -2.5 + (5.0/size)*start_x
        for jj in np.arange(0, xDiff):
            for kk in np.arange(0, 100):
                distance = get_range(radar_x[kk], radar_y[kk], radar_z[kk], x, y)
                ratio = (distance % range_bin_d) / range_bin_d
                index = math.floor(distance/range_bin_d)
                pulseArr[ii][jj] += (pulses[kk][index]*(1-ratio) + pulses[kk][index+1]*(ratio))
            magArr[ii][jj] = np.abs(pulseArr[ii][jj])
            x = x + 5.0/size
        y = y - 5.0/size
    return magArr

def fourier_approach(pulses, range_axis, platform_pos, x_vec, y_vec, 
                     center_freq):
    """
    Backprojection using shifts implemented through linear phase ramps.
    """
    # Determine dimensions of data
    (num_pulses, num_range_bins) = pulses.shape
    num_x_pos = len(x_vec)
    num_y_pos = len(y_vec)
    
    # Compute the fast-time or range-bin times
    fast_time = np.transpose(range_axis / SPEED_OF_LIGHT)
    delta_fast_time = fast_time[1] - fast_time[0]
    
    # Compute the unwrapped angular frequency
    ang_freq = np.transpose(2 * np.pi * 
                            np.arange(-num_range_bins / 2, num_range_bins / 2) / 
                            (delta_fast_time * num_range_bins))
    
    # X-Y locations of image grid
    x_grid, y_grid = np.meshgrid(x_vec, y_vec)
    
    # Initialize SAR image
    complex_image = np.zeros_like(x_grid, dtype=np.complex)
    
    # Iterate over each X-position in image grid and focus all the pixels 
    # across the Y-span of the image grid, i.e., a column
    for ii in range(0, num_x_pos):
        print('%d of %d' % (ii, num_x_pos))
        
        # Initialize current column's sum of aligned pulses
        sum_aligned_pulses = np.zeros(num_y_pos, dtype=np.complex)
        
        # Iterate over each pulse
        for jj in range(0, num_pulses):
            
            # Calculate the 2-way time delay to each point in the current 
            # column of the image grid
            two_way_time = 2 * np.sqrt(
                    (x_grid[:, ii] - platform_pos[jj, 0])**2 + 
                    (y_grid[:, ii] - platform_pos[jj, 1])**2 +
                    platform_pos[jj, 2]**2) / SPEED_OF_LIGHT
                    
            # Demodulate the current pulse
            demod_pulse = (np.transpose(np.atleast_2d(pulses[jj, :])) * 
                           np.exp(-1j * 2 * np.pi * center_freq * 
                                  (fast_time - two_way_time)))
            
            # Align the current pulses contribution to current column
            demod_pulse_freq = np.fft.fftshift(np.fft.fft(demod_pulse, axis=0),
                                               axes=0)
            phase_shift = np.exp(1j * np.outer(ang_freq, two_way_time))
            demod_pulse_freq_aligned = phase_shift * demod_pulse_freq
            pulse_aligned = np.fft.ifft(
                    np.fft.ifftshift(demod_pulse_freq_aligned, 0), axis=0)
            
            # Update current column's sum of aligned pulses
            sum_aligned_pulses += np.transpose(pulse_aligned[0])
            
        # Update complex image with latest column's result
        complex_image[:, ii] = sum_aligned_pulses
    return complex_image

def parse_args(args):
    """
    Input argument parser.
    """
    parser = argparse.ArgumentParser(
            description=('SAR image formation via backprojection'))
    parser.add_argument('input', nargs='?', type=str,
                        help='Pickle containing data')
    parser.add_argument('x_bounds', nargs=2, type=float, 
                        help=('Minimum and maximum bounds of the X coordinates'
                              ' of the image (m)'))
    parser.add_argument('y_bounds', nargs=2, type=float, 
                        help=('Minimum and maximum bounds of the Y coordinates'
                              ' of the image (m)'))
    parser.add_argument('pixel_res', type=float, help='Pixel resolution (m)')
    parser.add_argument('-o', '--output', nargs='?', const=None, default=None, 
                        type=str, help='File to store SAR image to')
    parser.add_argument('-m', '--method', nargs='?', type=str,
                        choices=('shift', 'interp', 'fourier'),
                        default='fourier', const='fourier', 
                        help='Backprojection method to use')
    parser.add_argument('-fc', '--center_freq', type=float, 
                        help=('Center frequency (Hz) of radar; must be '
                              'specified if using fourier method'))
    parser.add_argument('-nv', '--no_visualize', action='store_true', 
                        help='Do not show SAR image')
    parsed_args = parser.parse_args(args)
    
    # Do some additional checks
    if parsed_args.output is None:
        root, ext = os.path.splitext(parsed_args.input)
        parsed_args.output = '%s.png' % root
    
    return parsed_args

def main(args):
    """
    Top level methods
    """
    # Parse input arguments
    parsed_args = parse_args(args)
    
    # Load data
    with open(parsed_args.input, 'rb') as f:
        data = pickle.load(f)
    platform_pos = data[0]
    pulses = data[1]
    range_axis = data[2]
    
    # Determine X-Y coordinates of image pixels
    x_vec = np.arange(parsed_args.x_bounds[0], parsed_args.x_bounds[1], 
                      parsed_args.pixel_res)
    y_vec = np.arange(parsed_args.y_bounds[0], parsed_args.y_bounds[1], 
                      parsed_args.pixel_res)
    
    # Form SAR image
    if parsed_args.method == 'fourier':
        complex_image = fourier_approach(
                pulses, range_axis, platform_pos, x_vec, y_vec, 
                parsed_args.center_freq)
    else:
        raise ValueError('Unknown method %s specified' % parsed_args.method)    
        
    # Convert to magnitude image for visualization
    image = np.abs(complex_image)
        
    # Show SAR image
    if not parsed_args.no_visualize:
        image_extent = (x_vec[0], x_vec[-1], y_vec[0], y_vec[-1])
        plt.figure()
        plt.subplot(121)
        plt.imshow(image, origin='lower', extent=image_extent)
        plt.title('Linear Scale')
        plt.colorbar()
        plt.subplot(122)
        plt.imshow(20 * np.log10(image), origin='lower', extent=image_extent)
        plt.title('Logarithmic Scale')
        plt.colorbar()
        plt.show()
        
    # Save image
    plt.imsave(parsed_args.output, image)

#Stores the positions of the UAS
'''
radar_x = []
radar_y = []
radar_z = []
for position in data[0]:
    radar_x.append(position[0])
    radar_y.append(position[1])
    radar_z.append(position[2])


pulses = data[1]
range_bins = data[2][0]
range_bin_d = (range_bins[int(len(range_bins)/2)+1] - range_bins[int(len(range_bins)/2)])/2

# Initializes grid as a list of lists

pixel_values = list(list(0+0j for ii in np.arange(0, size)) for jj in np.arange(0, size))


# Calculating the color of each pixel in the image by iterating over all the pulses and summing the complex values within
# the correct range bins and ultimately storing the absolute value of the sum at the corresponding index in pixel_values 

y = 2.5
for ii in np.arange(0, size):
    print ("%d / %d" % (ii, size))
    x = -2.5
    for jj in np.arange(0, size):
        for kk in np.arange(0, 100):
            distance = get_range(radar_x[kk], radar_y[kk], radar_z[kk], x, y)
            ratio = (distance % range_bin_d) / range_bin_d
            index = math.floor(distance/range_bin_d)
            pixel_values[ii][jj] += (pulses[kk][index]*(1-ratio) + pulses[kk][index+1]*(ratio))
        pixel_values[ii][jj] = np.abs(pixel_values[ii][jj])
        x = x + 5.0/size
    y = y - 5.0/size
          
plt.imshow(pixel_values) # shows the image
#plt.imshow(edge_detection(pixel_values,1500)) # prints the image after edge detection

end = timeit.default_timer()
print(end-start) # prints the run time
'''
