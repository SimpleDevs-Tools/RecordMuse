import pandas as pd
import numpy as np
import argparse

TIMESTAMP_COLUMNS = ['TimeStamp', 'unix_ms', 'unix_ts', 'lsl_unix_ts']

def normalize(rest_src:str, exp_src:str, ts_col:str='lsl_unix_ts', start_buffer=5.0, end_buffer=5.0):

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
    out_filename = ''.join(os.path.basename(exp_src).splitext('.')[:-1]) + '_normalized.csv'
    outpath = os.path.join(os.path.dirname(exp_src), out_filename)
    print(outpath)
    #exp_norm.to_csv(outpath, index=False)

#    print("Normalization complete.")
 #   print(f"Used {len(rest_mid)} rest samples for baseline.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Normalize an EEG file based on a rest-state EEG sample")
    parser.add_argument('rest_eeg_src', help="The resting state EEG sample, as a csv file.", type=str)
    parser.add_argument('eeg_src', help='The EEG csv file to normalize', type=str)
    parser.add_argument('-tc', '--ts_col', help="The timestamp column", type=str, default='lsl_unix_ts')
    parser.add_argument('-sb', '--start_buffer', help='The time buffer to cull out from the beginning of the rest-state EEG', type=float, default=5.0)
    parser.add_argument('-eb', '--end_buffer', help='The time buffer to cull out from the end of the rest-state EEG', type=float, default=5.0)
    args = parser.parse_args()

