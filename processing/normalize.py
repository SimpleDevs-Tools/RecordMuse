import os
import numpy as np
import pandas as pd
import numpy as np
import argparse
import matplotlib.pyplot as plt
from scipy.signal import welch

TIMESTAMP_COLUMNS = ['TimeStamp', 'unix_ms', 'unix_ts', 'lsl_unix_ts']

# ============ VALIDATION FUNCTIONS ============

def sparkline(values):
    ticks = "▁▂▃▄▅▆▇█"
    values = np.asarray(values, dtype=float)
    if values.max() == 0:
        return ""
    scaled = (values - values.min()) / (values.max() - values.min())
    return "".join(ticks[int(v * (len(ticks) - 1))] for v in scaled)

def histogram_sparkline(values, bins=40, range=None):
    values = np.asarray(values, dtype=float)
    hist, _ = np.histogram(values, bins=bins, range=range)
    return sparkline(hist)

# ============ MAIN ============

def normalize(rest_src:str, exp_src:str, ts_col:str='lsl_unix_ts', start_buffer=5.0, end_buffer=5.0, validate:bool=False):

    # Load data
    rest_df = pd.read_csv(rest_src)
    exp_df  = pd.read_csv(exp_src)

    # Identify EEG channel columns
    channel_cols = [c for c in rest_df.columns if c not in TIMESTAMP_COLUMNS]

    # Sanity check
    missing = set(channel_cols) - set(exp_df.columns)
    if missing:
        raise ValueError(f"Experimental CSV missing channels: {missing}")

    # Cull rest EEG edges
    t_start = rest_df[ts_col].min() + start_buffer
    t_end   = rest_df[ts_col].max() - end_buffer

    rest_mid = rest_df[
        (rest_df[ts_col] >= t_start) &
        (rest_df[ts_col] <= t_end)
    ]

    if len(rest_mid) == 0:
        raise ValueError("Rest EEG empty after culling — check time column.")

    # Compute baseline statistics
    baseline_mean = rest_mid[channel_cols].mean()
    baseline_std  = rest_mid[channel_cols].std(ddof=0)

    # Prevent divide-by-zero
    baseline_std[baseline_std == 0] = np.nan

    # Normalize experimental EEG
    exp_norm = exp_df.copy()

    exp_norm[channel_cols] = (
        exp_df[channel_cols] - baseline_mean
    ) / baseline_std

    # Save result
    out_filename = ''.join(os.path.basename(exp_src).split('.')[:-1]) + '_normalized.csv'
    outpath = os.path.join(os.path.dirname(exp_src), out_filename)
    exp_norm.to_csv(outpath, index=False)

    print("Normalization complete.")
    print(f"Used {len(rest_mid)} rest samples for baseline.")

    # Validate
    if not validate: return outpath
    print("\n=== VALIDATION ===")

    print("-- Check 1: Mean and SD")
    rest_norm = (rest_mid[channel_cols] - baseline_mean) / baseline_std
    print("\nPer-channel mean (should be ~0):")
    print(rest_norm.mean())
    print("\nPer-channel std (should be ~1):")
    print(rest_norm.std())

    print("\n-- Check 2: Distribution Shape Preservation (They should be the same)")
    for ch in channel_cols:
        raw_vals  = exp_df[ch].values
        norm_vals = exp_norm[ch].values
        hist_range = (
            min(raw_vals.min(), norm_vals.min()),
            max(raw_vals.max(), norm_vals.max())
        )
        raw_s = histogram_sparkline(raw_vals, bins=30, range=hist_range)
        nor_s = histogram_sparkline(norm_vals, bins=30, range=hist_range)
        print(f"{ch:>6} | raw  {histogram_sparkline(raw_vals, bins=30)} | norm {histogram_sparkline(norm_vals, bins=30)}")

    print("\n-- Check 3: Frequency-Domain Validation (AF7)")
    fs = 256  # adjust if known
    x_rest = rest_mid['AF7'].to_numpy()
    x_exp  = exp_norm['AF7'].to_numpy()
    f, p_rest = welch(x_rest, fs=fs)
    _, p_exp  = welch(x_exp, fs=fs)
    plt.semilogy(f, p_rest, label="Rest")
    plt.semilogy(f, p_exp, label="Experiment (norm)")
    plt.legend()
    plt.title(f"PSD: AF7")
    plt.show()

    # Return outpath
    return outpath

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Normalize an EEG file based on a rest-state EEG sample")
    parser.add_argument('rest_src', help="The resting state EEG sample, as a csv file.", type=str)
    parser.add_argument('eeg_src', help='The EEG csv file to normalize', type=str)
    parser.add_argument('-tc', '--ts_col', help="The timestamp column", type=str, default='lsl_unix_ts')
    parser.add_argument('-sb', '--start_buffer', help='The time buffer to cull out from the beginning of the rest-state EEG', type=float, default=5.0)
    parser.add_argument('-eb', '--end_buffer', help='The time buffer to cull out from the end of the rest-state EEG', type=float, default=5.0)
    parser.add_argument('-v', '--validate', help="Should we validate if the normalization is correct?", action='store_true')
    args = parser.parse_args()
    normalize(args.rest_src, args.eeg_src, ts_col=args.ts_col, start_buffer=args.start_buffer, end_buffer=args.end_buffer, validate=args.validate)

