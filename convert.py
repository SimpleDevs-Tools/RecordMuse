import os
import argparse
import pandas as pd
import datetime

_MUSE_REMAPPINGS = { 'RAW_TP9':'TP9', 
                'RAW_TP10':'TP10', 
                'RAW_AF7':'AF7', 
                'RAW_AF8':'AF8', 
                'Accelerometer_X':'accel_x', 
                'Accelerometer_Y':'accel_y', 
                'Accelerometer_Z':'accel_z', 
                'Gyro_X':'gyro_x', 
                'Gyro_Y':'gyro_y',
                'Gyro_Z':'gyro_z'   }

def timestamp_to_unix_milliseconds(x) -> int:      # Helper: converts timestamps to unix
    date_format = datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")
    unix_seconds = datetime.datetime.timestamp(date_format)
    unix_milliseconds = int(unix_seconds * 1000)
    return unix_milliseconds

def timestamp_to_unix_seconds(x) -> int:      # Helper: converts timestamps to unix
    date_format = datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")
    unix_seconds = datetime.datetime.timestamp(date_format)
    return unix_seconds

def mm_to_bluemuse(target_filepath:str):
    
    df = pd.read_csv(target_filepath, dtype={'Elements':str})
    df['unix_ms'] = df['TimeStamp'].apply(timestamp_to_unix_milliseconds)
    df['lsl_unix_ts'] = df['TimeStamp'].apply(timestamp_to_unix_seconds)
    df = df.rename(columns=_MUSE_REMAPPINGS).sort_values('unix_ms')
    
    # Separate signals
    signals = df[df['Elements'].isna()]
    # Identify components
    eeg = signals[['TimeStamp', 'unix_ms', 'lsl_unix_ts', 'TP9', 'AF7', 'AF8', 'TP10']]
    accel = signals[['TimeStamp', 'unix_ms', 'lsl_unix_ts', 'accel_x', 'accel_y', 'accel_z']]
    gyro = signals[['TimeStamp', 'unix_ms', 'lsl_unix_ts', 'gyro_x',  'gyro_y', 'gyro_z']]
    # Rename colnames in accel and gyro dataframes
    accel = accel.rename(columns={'accel_x':'X','accel_y':'Y','accel_z':'Z'})
    gyro = gyro.rename(columns={'gyro_x':'X','gyro_y':'Y','gyro_z':'Z'})

    # output
    output_dir = os.path.join(os.path.dirname(target_filepath),'converted')
    os.makedirs(output_dir, exist_ok=True)
    eeg.to_csv(os.path.join(output_dir, 'EEG.csv'), index=False)
    accel.to_csv(os.path.join(output_dir, 'Accelerometer.csv'), index=False)
    gyro.to_csv(os.path.join(output_dir, 'Gyroscope.csv'), index=False)

# Example Usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert raw muse data from Mind Monitor into BlueMuse format")
    parser.add_argument('target', help="Relative path to the muse csv file that needs to be converted")
    args = parser.parse_args()
    mm_to_bluemuse(args.target)