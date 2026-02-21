import os
import numpy as np
import argparse
import pandas as pd
import datetime

_DESCRIPTION = "Convert raw muse data from Mind Monitor into BlueMuse format"

_MUSE_REMAPPINGS = { 'RAW_TP9':'TP9', 
                'RAW_TP10':'TP10', 
                'RAW_AF7':'AF7', 
                'RAW_AF8':'AF8',
                'AUX_RIGHT':'Right AUX',
                'AUX_LEFT':'Left AUX', 
                'Accelerometer_X':'accel_x', 
                'Accelerometer_Y':'accel_y', 
                'Accelerometer_Z':'accel_z', 
                'Gyro_X':'gyro_x', 
                'Gyro_Y':'gyro_y',
                'Gyro_Z':'gyro_z'   }

_EEG_COLUMNS = ['TimeStamp', 'TP9', 'AF7', 'AF8', 'TP10', 'Right AUX']
_EEG_COLUMNS_TS = ['TimeStamp', 'unix_ms', 'lsl_unix_ts', 'TP9', 'AF7', 'AF8', 'TP10', 'Right AUX']
_ACCEL_COLUMNS = ['TimeStamp', 'accel_x', 'accel_y', 'accel_z']
_ACCEL_COLUMNS_TS = ['TimeStamp', 'unix_ms', 'lsl_unix_ts', 'accel_x', 'accel_y', 'accel_z']
_GYRO_COLUMNS = ['TimeStamp', 'gyro_x',  'gyro_y', 'gyro_z']
_GYRO_COLUMNS_TS = ['TimeStamp', 'unix_ms', 'lsl_unix_ts', 'gyro_x',  'gyro_y', 'gyro_z']

_MUSE_SAMPLE_RATES = {
    'EEG':256,
    'IMU':52
}

def timestamp_to_unix_milliseconds(x) -> int:      # Helper: converts timestamps to unix
    date_format = datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")
    unix_seconds = datetime.datetime.timestamp(date_format)
    unix_milliseconds = int(unix_seconds * 1000)
    return unix_milliseconds

def timestamp_to_unix_seconds(x) -> int:      # Helper: converts timestamps to unix
    date_format = datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")
    unix_seconds = datetime.datetime.timestamp(date_format)
    return unix_seconds

def sample_synthetic_timestamps(n_samples:int, sfreq:int, start_unix_ms):
    dt_ms = 1000.0 / sfreq
    timestamps = (start_unix_ms + np.arange(n_samples) * dt_ms)
    return timestamps

def estimate_sample_rate_duration(df, timestamp_col="unix_ms", is_milli:bool=True):
    # Get timestamps
    ts = df[timestamp_col].to_numpy()
    ts = ts[~np.isnan(ts)]
    # Raise error if not enough samples
    if len(ts) < 2:
        raise ValueError("Not enough timestamps to estimate sample rate.")
    # Get the duration and number of samples, raise error if duration is wonky
    duration_sec = (ts[-1] - ts[0])
    if is_milli: duration_sec /= 1000.0
    n_samples = len(ts)
    if duration_sec <= 0:
        raise ValueError("Non-positive duration detected.")
    # Get the estimated sample rate
    fs_est = (n_samples - 1) / duration_sec
    return fs_est

# Straightforward. Only thing is to set a `unix_ms` based on the timestamps
def extract_blinks(df:pd.DataFrame):
    blinks = df[df['Elements'] == '/muse/elements/blink']                           # Only rows with blink in the `Elements`` col.
    blinks['unix_ms'] = blinks['TimeStamp'].apply(timestamp_to_unix_milliseconds)   # Blink timestamps set to `TimeStamp`
    blinks['lsl_unix_ts'] = blinks['TimeStamp'].apply(timestamp_to_unix_seconds)    # LSL timestamps based on `TimeStamp` too
    return blinks                                                                   # Return blinks

def extract_feature(df:pd.DataFrame, columns, sample_rate, start_unix_ms):
    raw = df[columns]
    deduped = df.groupby(columns, as_index=False).last()                                        # Remove duplicates
    deduped['unix_ms'] = sample_synthetic_timestamps(len(deduped), sample_rate, start_unix_ms)  # Calculate `unix_ms` and `lsl_unix_ts`
    deduped['lsl_unix_ts'] = deduped['unix_ms'].apply(lambda x: x*1000.0)                       # Calculate `lsl_unix_ts` from `unix_ms`
    return deduped

def read_mm_file(src:str):
    df = pd.read_csv(src)                                               # Read as a dataframe
    signals = df[df['Elements'].isna()]                                 # Get the signals first
    start_ms = timestamp_to_unix_milliseconds(signals.iloc[0]['TimeStamp'])  # get the first signal row as the first timestamp
    df = df.rename(columns=_MUSE_REMAPPINGS)                            # Rename the columns
    return df, start_ms

def mm_to_bluemuse(target_filepath:str, output_dir:str="converted", groupby_choice:str='last'):
    
    """
    # Read the data
    print("\033[4m=== Reading Mind Monitor File ===\033[0m")
    df, start_ms = read_mm_file(target_filepath)
    print("\033[31mStarting Timeestamp:\033[0m", start_ms)

    # Get blinks and signals
    print("\033[4m=== Extracting Blinks and Signals ===\033[0m")
    blinks = extract_blinks(df)
    signals = df[df['Elements'].isna()]
    print("\033[31m# Blink rows:\033[0m", len(blinks))
    print("\033[31m# Signal rows:\033[0m", len(signals))

    # Extract components
    print("\033[4m=== Extracting Components ===\033[0m")
    eeg = extract_feature(signals, _EEG_COLUMNS, _MUSE_SAMPLE_RATES['EEG'], start_ms)
    eeg = eeg[_EEG_COLUMNS_TS]
    eeg_fs = estimate_sample_rate_duration(eeg)
    accel = extract_feature(signals, _ACCEL_COLUMNS, _MUSE_SAMPLE_RATES['IMU'], start_ms)
    accel = accel[_ACCEL_COLUMNS_TS]
    accel = accel.rename(columns={'accel_x':'X','accel_y':'Y','accel_z':'Z'})
    accel_fs = estimate_sample_rate_duration(accel)
    gyro = extract_feature(signals, _GYRO_COLUMNS, _MUSE_SAMPLE_RATES['IMU'], start_ms)
    gyro = gyro[_GYRO_COLUMNS_TS]
    gyro = gyro.rename(columns={'gyro_x':'X','gyro_y':'Y','gyro_z':'Z'})
    gyro_fs = estimate_sample_rate_duration(gyro)
    print("\033[31m# EEG rows:\033[0m", len(eeg), f"({eeg_fs}Hz)")
    print("\033[31m# Accelerometer rows:\033[0m", len(accel), f"({accel_fs}Hz)")
    print("\033[31m# Gyroscope rows:\033[0m", len(gyro), f"({gyro_fs}Hz)")

    # Output
    print("\033[4m=== Saving and Outputting ===\033[0m")
    output_dir = os.path.join(os.path.dirname(target_filepath), output_dir)
    os.makedirs(output_dir, exist_ok=True)
    eeg_outpath = os.path.join(output_dir, 'EEG.csv')
    eeg.to_csv(eeg_outpath, index=False)
    accel_outpath = os.path.join(output_dir, 'Accelerometer.csv')
    accel.to_csv(accel_outpath, index=False)
    gyro_outpath = os.path.join(output_dir, 'Gyroscope.csv')
    gyro.to_csv(gyro_outpath, index=False)
    blinks_outpath = os.path.join(output_dir, 'BLINKS.csv')
    blinks.to_csv(blinks_outpath, index=False)
    return output_dir, eeg_outpath, accel_outpath, gyro_outpath, blinks_outpath
    """

    df = pd.read_csv(target_filepath, dtype={'Elements':str})
    df['unix_ms'] = df['TimeStamp'].apply(timestamp_to_unix_milliseconds)
    df['lsl_unix_ts'] = df['TimeStamp'].apply(timestamp_to_unix_seconds)
    df = df.rename(columns=_MUSE_REMAPPINGS).sort_values('unix_ms')
    
    # Separate blinks and signals
    blinks = df[df['Elements'] == '/muse/elements/blink']    
    signals = df[df['Elements'].isna()]
    # Identify components
    eeg_raw = signals[_EEG_COLUMNS_TS]
    eeg_groups = eeg_raw.groupby('TimeStamp', as_index=False)
    eeg = eeg_groups.last() if groupby_choice == 'last' else eeg_groups.first()
    accel_raw = signals[_ACCEL_COLUMNS_TS]
    accel_groups = accel_raw.groupby('TimeStamp', as_index=False)
    accel = accel_groups.last() if groupby_choice == 'last' else accel_groups.first()
    gyro_raw = signals[_GYRO_COLUMNS_TS]
    gyro_groups = gyro_raw.groupby('TimeStamp', as_index=False)
    gyro = gyro_groups.last() if groupby_choice == 'last' else gyro_groups.first()
    # Rename colnames in accel and gyro dataframes
    accel = accel.rename(columns={'accel_x':'X','accel_y':'Y','accel_z':'Z'})
    gyro = gyro.rename(columns={'gyro_x':'X','gyro_y':'Y','gyro_z':'Z'})

    # output
    if output_dir is None or len(output_dir) == 0: output_dir = "converted"
    output_dir = "[recording]-" + output_dir
    output_dir = os.path.join(os.path.dirname(target_filepath),output_dir)
    os.makedirs(output_dir, exist_ok=True)
    eeg_outpath = os.path.join(output_dir, 'EEG.csv')
    eeg.to_csv(eeg_outpath, index=False)
    accel_outpath = os.path.join(output_dir, 'Accelerometer.csv')
    accel.to_csv(accel_outpath, index=False)
    gyro_outpath = os.path.join(output_dir, 'Gyroscope.csv')
    gyro.to_csv(gyro_outpath, index=False)
    blinks_outpath = os.path.join(output_dir, 'BLINKS.csv')
    blinks.to_csv(blinks_outpath, index=False)
    return output_dir, eeg_outpath, accel_outpath, gyro_outpath, blinks_outpath


# Example Usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=_DESCRIPTION)
    parser.add_argument('target', help="Relative path to the muse csv file that needs to be converted")
    parser.add_argument('-od', '--output_dir', help="The name of the output directory, which will be created relative to the same directory as the target file", default="converted")
    parser.add_argument('-gbc', '--groupby_choice', help="Should we groupby and then use the last or first?", type=str, choices=['last','first'], default='last')
    args = parser.parse_args()
    mm_to_bluemuse(args.target, output_dir=args.output_dir, groupby_choice=args.groupby_choice)