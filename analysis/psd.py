import os
import numpy as np
import pandas as pd
import argparse
from scipy.signal import spectrogram, get_window
import matplotlib.pyplot as plt

# ========== CONFIG ==========

CHANNELS = ['AF7', 'AF8', 'TP9', 'TP10']
BANDS = {
    "delta": (1, 4),
    "theta": (4, 8),
    "alpha": (9, 13),
    "beta": (13, 30),
    "gamma": (30, 200)
}
CHANNEL_COLORS = {
    'AF7':'blue',
    'AF8':"purple",
    'TP9':'red',
    'TP10':'orange'
}
BAND_COLORS = {
    'delta': 'red',
    'theta': 'purple',
    'alpha': 'blue',
    'beta': 'green',
    'gamma': 'orange'
}
SAMPLE_RATE = 256
WINDOW_SIZE = 256
SLIDE_RATE = 22


# ========== PSD Computation ==========

def compute_muse_psd(df:pd.DataFrame):

    # Get the hamming window class with the defined window size
    win = get_window('hamming', WINDOW_SIZE)
    
    # Intiialize outputs
    psd = {}
    freqs = None
    times = None
    
    # For each channel, we:
    for ch in CHANNELS:
        # use `spectrogram` helper to calculate properties of the raw EEG signal in that channel
        f, t, Sxx = spectrogram(
            df[ch].values,
            fs = SAMPLE_RATE,
            window = win,
            nperseg = WINDOW_SIZE,
            noverlap = WINDOW_SIZE - SLIDE_RATE,
            scaling = 'density',
            mode = 'psd'
        )
        # Convert to decibels (dB)
        Sxx_dB = 10 * np.log10(Sxx + 1e-12)
        
        # Add our responses to out outputs. We only do this once.
        psd[ch] = Sxx_dB
        if freqs is None:
            freqs = f
            times = t
    
    # Return the three data extracted from all eeg channels
    return freqs, times, psd

# ========== PSD PLOTTING ==========

def plot_muse_psd(
    psds,
    title = True,
    cmap = 'viridis',
    zmin = -40, 
    zmax = 20,
    width = 3000, 
    height = 500,
    dpi = 100,
    savename = None,
    show_plot:bool=True
):
    # How many channels do we have?
    n_rows = len(psds)
    n_cols = len(CHANNELS)

    # Define the subplot grid
    fig, axes = plt.subplots( n_rows, n_cols, figsize=(width/dpi, height/dpi), dpi=dpi, constrained_layout=True)

    # Make the axis iterable
    if n_rows == 1 and n_cols == 1: axes = np.array([[axes]])
    elif n_rows == 1:               axes = np.array([axes])
    elif n_cols == 1:               axes = np.array([[ax] for ax in axes])

    # Start plotting
    for row_index in range(len(psds)):
        pre_title = f"{psds[row_index]['pre_title']} " if 'pre_title' in psds[row_index] else ""
        freqs = psds[row_index]['freqs']
        times = psds[row_index]['times']
        psd = psds[row_index]['psd']

        for col_index, ch in enumerate(CHANNELS):
            ax = axes[row_index][col_index]
            data = psd[ch]

            im = ax.imshow(
                data,
                aspect='auto',
                origin='lower',
                extent=[times[0], times[-1], freqs[0], freqs[-1]],
                cmap=cmap,
                vmin=zmin, vmax=zmax
            )
            ax.set_title(f"{pre_title} Channel = {ch}")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Freq (Hz)")

    # Add colorbar
    cbar = fig.colorbar(im, shrink=0.95)
    cbar.set_label("Power (dB)")

    # Add global title
    if title is not None: 
        if isinstance(title, bool): title = "Muse EEG Power Spectral Density (PSD)" 
        fig.suptitle(title, fontsize=14)

    # Save or show
    if savename is not None:    
        plt.savefig(savename, bbox_inches="tight")
    if show_plot:   plt.show()
    else:           plt.clf()

# ========== TIME SERIES BANDPOWERS ==========

def compute_bandpowers_time_series(
        freqs, 
        times, 
        psd, ):
    
    records = []
    for ch, Sxx_dB in psd.items():
        # Convert back from dB to linear scale
        Sxx_linear = 10 ** (Sxx_dB / 10)

        for band, (fmin, fmax) in BANDS.items():
            idx = np.where((freqs >= fmin) & (freqs <= fmax))[0]

            if len(idx) == 0:
                continue

            # Sum across frequency bins, keep per-time-frame values
            band_power = np.sum(Sxx_linear[idx, :], axis=0)

            # Logarithm → absolute band power
            band_power_log = np.log10(band_power + 1e-12)

            for t, val in zip(times, band_power_log):
                records.append((t, ch, band, val))

    bandpowers = pd.DataFrame(records, columns=["time", "channel", "band", "power"])
    return bandpowers

# ========== PLOT TIME SERIES ==========

def plot_time_series(
        df, 
        x_col, 
        y_col, 
        c_col, 
        facet_col=None, 
        facet_row=None, 
        color_dict      = None, 
        labels          = None, 
        title:str       = None, 
        width:float     = 3000, 
        height:float    = 500, 
        dpi:int         = 100,
        sharex          = False,
        sharey          = False,
        savename:str    = None,
        show_plot:bool  = True
):

    # Define axis labels
    x_label = labels[x_col] if labels is not None and x_col in labels else x_col
    y_label = labels[y_col] if labels is not None and y_col in labels else y_col

    # Determine facet structure
    facet_row_values = df[facet_row].unique() if facet_row else [None]
    facet_col_values = df[facet_col].unique() if facet_col else [None]
    nrows = len(facet_row_values)
    ncols = len(facet_col_values)

    # Create subplots
    fig, axes = plt.subplots(nrows, ncols, figsize=(width/dpi,height/dpi), dpi=dpi, sharex=sharex, sharey=sharey, constrained_layout=True)

    # Make axes iterable
    if nrows == 1 and ncols == 1:   axes = np.array([[axes]])
    elif nrows == 1:                axes = np.array([axes])
    elif ncols == 1:                axes = np.array([[ax] for ax in axes])

    # Plotting
    for i, r_val in enumerate(facet_row_values):
        for j, c_val in enumerate(facet_col_values):
            
            # Create a reference to the current axis
            ax = axes[i, j]

            # Get a subset of your DF
            subset = df.copy()
            if facet_row:   subset = subset[subset[facet_row] == r_val]
            if facet_col:   subset = subset[subset[facet_col] == c_val]

            # Plot the groups based on color
            for group, gdf in subset.groupby(c_col):
                color = color_dict[group] if color_dict and group in color_dict else None
                ax.plot(gdf[x_col], gdf[y_col], label=str(group), color=color)
            
            # Facet Titles
            title_parts = []
            if facet_row: title_parts.append(f"{facet_row} = {r_val}")
            if facet_col: title_parts.append(f"{facet_col} = {c_val}")
            ax.set_title(", ".join(title_parts))
            if i == nrows - 1:  ax.set_xlabel(x_label)
            if j == 0:          ax.set_ylabel(y_label)

            # Legend
            if i == 0 and j == 0:   ax.legend()
    
    # Global plot qualities
    if title is not None:
        fig.suptitle(title, fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    # Save if needed
    if savename is not None:    
        plt.savefig(savename, bbox_inches='tight')
    if show_plot:               plt.show()
    else:                       plt.clf()


# ========== MAIN FUNCTION ==========

def calculate_psd(src):
    # Read the pandas dataframe
    df = pd.read_csv(src)

    # Generate output directory, which save everything to a `plots` directory in the same directory as the provided file
    csv_output_dir = os.path.dirname(src)
    plot_output_dir = os.path.join(csv_output_dir,'plots')
    os.makedirs(plot_output_dir, exist_ok=True)

    # Compute and plot freqs, times, and psd
    freqs, times, psd = compute_muse_psd(df)
    psd_outpath = os.path.join(plot_output_dir,'psd.png')
    plot_muse_psd([{'freqs':freqs, 'times':times, 'psd':psd}], savename=psd_outpath)

    # Compute and plot time series
    bandpowers = compute_bandpowers_time_series(freqs, times, psd)
    bandpowers_outpath = os.path.join(plot_output_dir,'bandpowers.png')
    plot_time_series(
        bandpowers, 
        x_col='time', 
        y_col='power', 
        c_col='band', 
        facet_col='channel', 
        color_dict=BAND_COLORS, 
        labels={
            "power": "Abs. Power (Bels)", 
            "time": "Time (s)"}, 
        title="Time-resolved Absolute Band Power",
        savename = bandpowers_outpath
    )

    # Save bandpowers as a csv file
    bandpowers.to_csv(os.path.join(csv_output_dir, 'bandpowers.csv'), index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Produces PSD plots, based on EEG data. Recommend to filter first using `filter.py`.")
    parser.add_argument('src', help="Provide the relative filepath to your raw EEG file.", type=str)
    args = parser.parse_args()
    calculate_psd(args.src)