import os
import glob
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math

FILES = ['EEG.csv', 'Accelerometer.csv', 'Gyroscope.csv']
TIMESTAMP_COLUMNS = ['TimeStamp', 'unix_ms', 'unix_ts', 'lsl_unix_ts']
EXCLUSIONS = ['BANDPOWERS.csv', 'mind_monitor.csv']


# ============ DUPLICATE IDENTIFICATION ============

def get_consecutive_duplicates(df:pd.DataFrame, columns):
    change_mask = df[columns].ne(df[columns].shift()).any(axis=1)
    group_ids = change_mask.cumsum()
    df2 = df.assign(
        consecutive_count = df.groupby(group_ids).cumcount() + 1,
        count = df.groupby(group_ids)[columns[0]].transform('size')
    )
    dist = df2['count'].value_counts().sort_index()
    return dist


# =========== PLOTTING ============

def plot_raw(filename:str, df:pd.DataFrame, ts_col:str, with_lines:bool=False, outpath:str=None):

    # Identify the name of this plot
    stream_name = os.path.splitext(filename)[0]
    
    # Identify data columns
    data_cols = [col for col in df.columns if col not in TIMESTAMP_COLUMNS]
    num_channels = len(data_cols)    
    if num_channels == 0:
        print(f"Skipping {filename}: No data channels found.")
        return

    # Create a figure with one subplot per channel
    fig, axes = plt.subplots(nrows=num_channels, ncols=1, figsize=(12, 3 * num_channels), sharex=True)
    n_ticks = 5

    # If there's only one channel, axes is not a list, so we wrap it
    if num_channels == 1:
        axes = [axes]
        
    # Use timestamp for the X-axis (relative to the start of the recording)
    #time_x = df[ts_col] - df[ts_col].iloc[0]
    for i, col in enumerate(data_cols):
        axes[i].scatter(df[ts_col], df[col], label=col, color='tab:blue', s=0.5)
        if with_lines:
            axes[i].plot(df[ts_col], df[col], label=col, color='tab:blue', alpha=0.25, linewidth=1)
        axes[i].set_ylabel(col)
        xmin, xmax = axes[i].get_xlim()
        axes[i].set_xticks(np.linspace(xmin, xmax, n_ticks))
        axes[i].grid(True, linestyle='--', alpha=0.6)

    # Additional plotting details such as title and x-axis labels
    axes[-1].set_xlabel("Time")
    fig.suptitle(f"Signal Performance: {stream_name} Recording", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    # Save to a PNG file
    if outpath is not None:
        plt.savefig(outpath, bbox_inches='tight')
    plt.close(fig)
    print(f"Generated {stream_name} from {filename}")


# ============ MAIN ============

def validate(src_dir:str, ts_col:str, with_lines:bool=False, show:bool=False):

    # Find all CSV files in the directory
    csv_files = glob.glob(os.path.join(src_dir, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {src_path}")
        return

    # Validating if filename is in the excluded files or not
    files = []
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        if filename in EXCLUSIONS:
            print("[EXCL] Ignoring", filename)
            continue
        files.append(file_path)

    # create an appropriate output directory where all plots are to be saved in
    out_dir = os.path.join(src_dir, 'plots')
    os.makedirs(out_dir, exist_ok=True)

    # Create a super figure
    ncols = 3
    nrows = math.ceil(len(files)/ncols)
    fig = plt.figure(figsize=(nrows*4, ncols*2), layout=None)
    gs = fig.add_gridspec(nrows, ncols, hspace=0.3, wspace=0.15, top=0.9)

    # Iterate through all files
    for i, file_path in enumerate(files):
        col_index = i % ncols
        row_index = math.floor(i/ncols)
        filename = os.path.basename(file_path)
        stream_name = os.path.splitext(filename)[0]

        # Read and plot raw data
        df = pd.read_csv(file_path)
        df_cols = [col for col in df.columns if col not in TIMESTAMP_COLUMNS]
        raw_plot_outpath = os.path.join(out_dir, f"{stream_name}.png")
        plot_raw(filename, df, ts_col, with_lines=with_lines, outpath=raw_plot_outpath)

        # Identify duplicates
        dupes1 = get_consecutive_duplicates(df, [ts_col])
        dupes2 = get_consecutive_duplicates(df, [ts_col, *df_cols])
        dupes = pd.concat([dupes1, dupes2], axis=1).fillna(0)
        dupes.columns = [f"TS ({ts_col})", 'TS & Columns']
        
        # Plot duplicates
        ax = fig.add_subplot(gs[row_index, col_index])
        dupes.plot.bar(ax=ax, width=0.8, edgecolor='black')
        ax.set_title(stream_name)
        show_legend = i == 0
        ax.legend().set_visible(show_legend)

    # Modify the super figure
    fig.suptitle('Duplicates Identified')

    # Save fig
    dupes_plot_outpath = os.path.join(out_dir, 'duplicates.png')
    plt.savefig(dupes_plot_outpath, bbox_inches='tight')
    if show:    plt.show()
    else:       plt.close()
    print(f"Generated duplicates: {dupes_plot_outpath}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validates all files in a provided directory. These include finding duplicates and producing raw data plots.")
    parser.add_argument('src', help="The directory where your EEG, Accelerometer, and Gyroscope data are stored.", type=str)
    parser.add_argument('-tc', '--timestamp_colname', help='The representative timestamp to identify duplicates with', type=str, default='unix_ms')
    parser.add_argument('-wl', '--with_lines', help="When plotting raw plots, should we also render lines to connect raw scatter points?", action='store_true')
    parser.add_argument('-p', '--preview', help="Should we show the duplicate plot at the end?", action='store_true')
    args = parser.parse_args()
    validate(args.src, args.timestamp_colname, args.with_lines, args.preview)