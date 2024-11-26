# %% 
#####
#
# RealSpaceMethod_SI.py
#
#####
#
# by Nathan Brichta, Levi Tegg, Luke Giles, John E. Daniels, Julie M. Cairney.
#
# ===================================================================================
# The input is a micrograph of the image analysed in ImageJ, along with the
# .csv file generated from ImageJ containing the line profile distance data 
# (x axis), and pixel intensity data (y-axis).
# It creates a figure with three panels:
#   (a) The original microscopy image (left)
#   (b) Example line profiles showing intensity variations (top right)
#   (c) Histogram distribution of domain widths with Gaussian fitting (bottom right)
# ===================================================================================
# 
# AI Assistance:
# Parts of this code were rewritten for syntax correction and formatting clarity 
# using large language models ChatGPT 4o mini (OpenAI, 2024) and Claude 3.5 Sonnet (Anthropic, 2024)
#
# Includes functions from Yoan Tournade's GitHub repository detailing Python peak-finding algorithms:
# https://github.com/MonsieurV/py-findpeaks
# which is licensed under the MIT license, reproduced below:
#
# Copyright (c) 2024 Yoan Tournade <yoan@ytotech.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#%% Import libraries

# Core Python packages
import os  # Operating system interface: for file and path operations
import glob  # File pattern matching: used to find CSV files matching patterns

# Data handling and numerical computation
import pandas as pd  # DataFrame operations: reading and manipulating CSV data
import numpy as np  # Numerical operations: arrays, mathematical functions, statistics

# Scientific computation
from scipy.signal import find_peaks  # Signal processing: detecting peaks in intensity profiles
from scipy.stats import norm  # Statistical functions: normal distribution fitting
from scipy.optimize import curve_fit  # Curve fitting: fitting Gaussian to histogram data

# Visualization packages
import matplotlib  # Base plotting library
import matplotlib.pyplot as plt  # Main plotting interface
from matplotlib.gridspec import GridSpec  # Custom layout management for subplots
import matplotlib.patches as patches  # Shapes and arrows for annotations
from PIL import Image  # Image handling: reading and basic image operations

#%% General script options

# Set matplotlib parameters for consistent figure styling
plt.rcParams.update({'mathtext.default': 'regular',
                    'mathtext.fontset':'custom',
                    'font.sans-serif': ['FreeSans', 'Tahoma', 'Arial'],
                    'mathtext.it':'FreeSans:italic',
                    'mathtext.rm':'FreeSans',    
                    'mathtext.cal':'Lucida Sans Unicode',
                    'xtick.labelsize': 8,
                    'ytick.labelsize': 8,
                    'lines.linewidth': 1.0})

# Define colors and labels for different regions in the analysis
colors = [ # These are the default colors used by matplotlib for editing or reference.
    '#1f77b4',  # Blue
    '#ff7f0e',  # Orange
    '#2ca02c',  # Green
    '#d62728',  # Red
    '#9467bd',  # Purple
    '#8c564b'   # Brown
]
labels = [ # Specifying regions of interest for labelling purposes. 
    'Region 1', 
    'Region 2',
    'Region 3',
    'Region 4',
    'Region 5',
    'Region 6',
]

# Peak detection parameters
NanoWidth = 1.2  # Minimum width between peaks (in nanometers), calculated using the median filter window size in pixels, converted to nm.
PeakProm = (0)  # Minimum peak prominence for detection

#%% File import parameters

# Micrograph file
directory = '.'  # Current directory for data files
filename = 'image.png'  # Input image file
nm_per_pixel = 0.240688  # Scale calibration: nanometers per pixel


# CSV file
files = [file for file in os.listdir(directory) if not file.startswith('._')]
files = glob.glob('profiledata*.csv') # Finds all CSV files that start with "profiledata"


#%% Figure layout via GridSpec

# 3 rows, 2 columns with custom height ratios
fig = plt.figure(figsize=(7.48, 4), dpi=120)
gs = GridSpec(3, 2, height_ratios=[5, 1, 1], width_ratios=[1, 1])

# Panel (a): Display the microscopy image
ax_img = fig.add_subplot(gs[:, 0])
img = np.array(Image.open(filename))
ax_img.imshow(img)
ax_img.axis('off')
ax_img.set_title(r'(a) Image, $\mathit{I}_{filter}$', loc='left', fontsize=9)

# Panel (c): Create histogram plot
ax_hist = fig.add_subplot(gs[1:, 1])

#%% CSV data importing *SEE COMMENT BLOCK*

# Process each CSV file (representing different regions)
for i, file in enumerate(files):
    if file.endswith('.csv'):
        # Read line profile data from CSV
        filepath = os.path.join(directory, file)
        df = pd.read_csv(filepath)
        
        # ===================
        # Depending on how your ImageJ ROI profile data is saved, you will either have
        # a .csv file that contains only 1 column of distance values and successive 
        # columns of pixel intensity (Option A), or you will have alternating 
        # distance-intensity columns (Option B). You will need to comment/uncomment
        # the relevant code sections below depending on the format.
        # ===================
        
# ---------------- (A) Same x values ----------------------------- 

        # # Extract x values from first column and y values from all other columns
        # x_arrays = []
        # y_arrays = []
        # x_values = df.iloc[:, 0].values  # Get x values from first column only
        # # Get y values from all remaining columns
        # for col_index in range(1, len(df.columns)):
        #     y_values = df.iloc[:, col_index].values
        #     x_arrays.append(x_values)  # Reuse the same x values
        #     y_arrays.append(y_values)
        
# ---------------- (B) Alternating x/y values ---------------- 

        # Extract x and y values from alternating columns
        x_arrays = []
        y_arrays = []
        for col_index in range(0, len(df.columns), 2):
            x_values = df.iloc[:, col_index].values
            y_values = df.iloc[:, col_index + 1].values
            x_arrays.append(x_values)
            y_arrays.append(y_values)

# %% Domain width calculation
        
        # Convert to numpy arrays and apply scale calibration
        x_arrays = np.array(x_arrays) * nm_per_pixel
        y_arrays = np.array(y_arrays)

        # Find peaks in intensity profiles 
        # (Templated from Yoan Tournade's find_peaks example at 
        # https://github.com/MonsieurV/py-findpeaks)
        peaks_indices = []
        for x, y in zip(x_arrays, y_arrays):
            peaks, _ = find_peaks(-y, width=NanoWidth, prominence=PeakProm)
            peaks_indices.append(peaks)

        # Calculate domain widths from peak distances
        DomainWidths = np.concatenate([np.diff(array) for array in peaks_indices])

#%% Outlier removal
        
        # Remove statistical outliers using 1.5 × IQR method
        Q1 = np.percentile(DomainWidths, 25)
        Q3 = np.percentile(DomainWidths, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        DomainWidths = [x for x in DomainWidths if x >= lower_bound and x <= upper_bound]
        
#%% Histogram generation & curve-fitting
        
        # Create histogram bins and plot
        binlist = np.linspace(0, 160, 50)
        counts, bins, _ = ax_hist.hist(DomainWidths, bins=binlist, histtype='step', 
                                     lw=0.5, color=colors[i], label=labels[i])
        
        # Fit Gaussian curve to histogram data
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        params = norm.fit(DomainWidths)
        
        def Gaussian(x, a, b, c, d):
            """Gaussian function with offset"""
            return d + a*np.exp((-(x-b)**2)/(2*c**2))
        
        # Fit Gaussian curve using scipy's curve_fit
        params, params_err = curve_fit(
            Gaussian,
            bins[:-1],
            counts[:],
            p0 = (20, 73, 40, 0)  # Initial parameter guess
        )
        paramsLTerr = np.sqrt(np.diag(params_err))
        
        # Plot fitted Gaussian curve
        ax_hist.plot(np.linspace(0, 120), Gaussian(np.linspace(0, 120), *params), 
                    ls='--', color=colors[i])
        
        # # *UNCOMMENT IF NEEDED* Save histogram data to CSV 
        # np.savetxt(f'RealSpaceMethodHist_{i}.csv', 
        #           np.array([bins[:-1], counts]).T, 
        #           delimiter=',', fmt='%9f', 
        #           header='Bins, counts')

#%% Add figures/annotations to subplot

# Panel (b): Plot example line profiles
ax_profiles = fig.add_subplot(gs[0, 1])
for idx, (x, y) in enumerate(zip(x_arrays[:4], y_arrays[:4])):
    # Plot profile with vertical offset for visibility
    ax_profiles.plot(x, y + 200 * idx, color='grey', label=f'Array {idx+1}')
    # Mark detected peaks
    peaks, _ = find_peaks(-y, width=NanoWidth, prominence=PeakProm)
    ax_profiles.plot(x[peaks], y[peaks] + 200 * idx, 'r|', markersize=5)

# Add scale bar to microscopy image
scale_length_nm = 250
scale_length_px = scale_length_nm / 0.962752  # Convert to pixels
scale_bar = patches.Rectangle((0, 1040), scale_length_px, 25, 
                            edgecolor='k', lw=0, facecolor='k', clip_on=False)
ax_img.add_patch(scale_bar)
ax_img.text(scale_length_nm + 30, 1065, f'{scale_length_nm} nm', fontsize=8, va='baseline')

# Add arrows to highlight features (coordinates are in pixels)
# Black arrows for large domain boundaries
arrow_params = [(770, 1080, 745, 1030), (690, 1080, 660, 1030)]
for x1, y1, x2, y2 in arrow_params:
    ax_img.add_patch(patches.FancyArrowPatch(
        (x1, y1), (x2, y2), 
        shrinkA=0, shrinkB=0, color="black", 
        arrowstyle="-|>", clip_on=False,
        linewidth=1, mutation_scale=10))

# Red arrows for nano-domain boundaries
nano_arrows = [
    (885, 1080, 905, 1030), (855, 1080, 875, 1030),
    (532, 1080, 552, 1030), (510, 1080, 530, 1030),
    (485, 1080, 505, 1030), (455, 1080, 475, 1030)
]
for x1, y1, x2, y2 in nano_arrows:
    ax_img.add_patch(patches.FancyArrowPatch(
        (x1, y1), (x2, y2),
        shrinkA=0, shrinkB=0, color="r",
        arrowstyle="-|>", clip_on=False,
        linewidth=1, mutation_scale=10))

# Add region labels
ax_img.text(305, 80, f'{labels[0]}', ha='center', fontsize=9, color='w')
ax_img.text(705, 80, f'{labels[1]}', ha='center', fontsize=9, color='w')

# Set axis properties for histogram and profile plots
ax_hist.set_xlabel('Width (nm)', fontsize=9)
ax_hist.set_ylabel('Frequency', fontsize=9)
ax_hist.set_xlim([0, 125])
ax_hist.set_yticks([])
ax_hist.set_title('(c) Nanodomain width distribution', loc='left', fontsize=9)

ax_profiles.set_title('(b) Line profile examples', loc='left', fontsize=9)
ax_profiles.set_yticks([])
ax_profiles.set_xlabel('Distance (nm)', fontsize=9)
ax_profiles.set_xlim([0, 425])

# Add legend to histogram
handle1 = matplotlib.lines.Line2D([], [], color=colors[0], lw=0.5, label=labels[0])
handle2 = matplotlib.lines.Line2D([], [], color=colors[1], lw=0.5, label=labels[1])
handle3 = matplotlib.lines.Line2D([], [], ls='--', color='0.5', label='Fit')
ax_hist.legend(handles=[handle1, handle2, handle3], loc='upper right', 
               frameon=False, fontsize=8, handlelength=2, handletextpad=0.5)

# Adjust layout and save figure
plt.tight_layout()
plt.show()
fig.savefig('RealSpaceMethod.png', dpi=1200, bbox_inches='tight')
fig.savefig('RealSpaceMethod.pdf', dpi=1200, bbox_inches='tight')
