import os
import pandas as pd
from collections import defaultdict
import argparse
from check_config import load_presets, normalize, match_single_csv

def split_mind_monitor(
    df:pd.DataFrame
) -> dict:
    """
    Given a Mind Monitor dataframe, split it into different representative streams
    """

    # Prepare the output dictionary, which contains a df for each stream type
    streams = {}

    # Helper function: checker to see if a stream has the appropriate amount of columns
    def has_cols(cols, threshold=0.6):
        present = [c for c in cols if c in df.columns]
        return len(present) / len(cols) >= threshold

    # EEG (RAW)
    eeg_cols = ["TimeStamp", "RAW_TP9", "RAW_AF7", "RAW_AF8", "RAW_TP10", "AUX_RIGHT"]
    if has_cols(eeg_cols):
        streams["EEG"] = df[eeg_cols].rename(columns={
            "RAW_TP9": "TP9",
            "RAW_AF7": "AF7",
            "RAW_AF8": "AF8",
            "RAW_TP10": "TP10",
            "AUX_RIGHT": "Right AUX"
        })

    # Accelerometer
    accel_cols = ["TimeStamp", "Accelerometer_X", "Accelerometer_Y", "Accelerometer_Z"]
    if has_cols(accel_cols):
        streams["Accelerometer"] = df[accel_cols].rename(columns={
            "Accelerometer_X": "X",
            "Accelerometer_Y": "Y",
            "Accelerometer_Z": "Z"
        })

    # Gyroscope
    gyro_cols = ["TimeStamp", "Gyro_X", "Gyro_Y", "Gyro_Z"]
    if has_cols(gyro_cols):
        streams["Gyroscope"] = df[gyro_cols].rename(columns={
            "Gyro_X": "X",
            "Gyro_Y": "Y",
            "Gyro_Z": "Z"
        })

    # PPG
    ppg_cols = ["TimeStamp", "PPG_Ambient", "PPG_IR", "PPG_Red"]
    if has_cols(ppg_cols):
        streams["PPG"] = df[ppg_cols].rename(columns={
            "PPG_Ambient": "Ambient",
            "PPG_IR": "Infrared",
            "PPG_Red": "Red"
        })

    # Return output dictionary.
    return streams

def find_target_stream(
    presets:dict, 
    target_config:str, 
    stream_name:str
):
    """
    Query the yaml configuration `presets` with a query config `target_config` and stream name config `stream_name`.
    If a match is found, then we return that stream.
    """
    for s in presets[target_config]:
        if s["name"].lower() == stream_name.lower():
            return s
    return None

def convert_dataframe(
    df:pd.DataFrame, 
    target_stream:dict
) -> pd.DataFrame:
    """
    Given a 
    """
    norm_cols = {normalize(c): c for c in df.columns}
    new_df = pd.DataFrame()

    if "timestamp" in norm_cols:
        new_df["TimeStamp"] = df[norm_cols["timestamp"]]

    for ch in target_stream["channels"]:
        key = normalize(ch)
        if key in norm_cols:
            new_df[ch] = df[norm_cols[key]]

    return new_df

def convert_file(
    filepath:str, 
    presets:dict, 
    target_config:str, 
    output_path:str = None,
    mm_groupby_choice:str = "last"
):
    # Given a file path, interpret it as a DataFrame
    df = pd.read_csv(filepath)

    # We want to find which configuration this best matches with
    # If an error occurs (i.e. no match), then we forget this file.
    match = match_single_csv(df, presets)
    if not match:   return None

    # Get the configuration name
    source_config = match["config"]

    # Prepare outputs
    outputs = []

    # Special case: Mind Monitor. 
    # In this case, we have to separate into different dataframes
    if source_config == "mind_monitor":
        # Prepare output directory
        base_dir = os.path.dirname(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        if output_path and os.path.isdir(output_path):
            out_dir = output_path
        else:
            out_dir = os.path.join(base_dir, f"{base_name}_{target_config}")
        os.makedirs(out_dir, exist_ok=True)

        # Split the single dataframe into individual streams
        split_streams = split_mind_monitor(df)
        # Prepare the outputs
        outputs = []

        # For each identified split from the mind monitor data:
        for stream_name, sub_df in split_streams.items():
            # Check what kind of stream it best corresponds with.
            # If a target stream match isn't found, then we ignore.
            target_stream = find_target_stream(presets, target_config, stream_name)
            if not target_stream:   continue

            # Generate the outpath, using the new output directory
            out_path = os.path.join(out_dir, f"{stream_name}.csv")

            # We first generate the converted dataframe
            new_df = convert_dataframe(sub_df, target_stream)

            # We then groupby and then get the last
            if mm_groupby_choice != 'none':
                groups = new_df.groupby('TimeStamp', as_index=False)
                new_df = groups.last() if mm_groupby_choice == 'last' else eeg_groups.first()
            
            # Finally, we save the stream file, and record our operation
            new_df.to_csv(out_path, index=False)
            outputs.append(out_path)

        # Return the outputs
        return outputs

    # Normal case - likely either Petal Metrics or BlueMuse
    # If target stream cannot be found, we ignore
    target_stream = find_target_stream(presets, target_config, match["name"])
    if not target_stream:   return None

    # Create a new dataframe
    new_df = convert_dataframe(df, target_stream)

    # Derive the output path, if not given
    if output_path:
        out_path = output_path
    else:
        base = os.path.splitext(filepath)[0]
        out_path = f"{base}_{target_config}.csv"

    # Save the result, and report a single-file output.
    new_df.to_csv(out_path, index=False)
    return [out_path]

def convert_directory(
    dir_path:str,
    presets:dict,
    target_config:str,
    output_dir=None,
    valid_patterns=None
):
    parent = os.path.dirname(dir_path)
    dirname = os.path.basename(dir_path)

    if output_dir is None:
        output_dir = os.path.join(parent, f"{dirname}_{target_config}")

    os.makedirs(output_dir, exist_ok=True)

    compiled_patterns = None
    if valid_patterns:
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in valid_patterns]

    results = []

    for f in os.listdir(dir_path):
        if not f.endswith(".csv"):
            continue

        if compiled_patterns:
            if not any(p.search(f) for p in compiled_patterns):
                continue

        in_path = os.path.join(dir_path, f)

        out_base = os.path.splitext(f)[0]
        out_path = os.path.join(output_dir, f"{out_base}_{target_config}.csv")

        res = convert_file(in_path, presets, target_config, output_path=out_path)

        if res:
            results.extend(res)

    return output_dir, results

def convert_input(
    src_path:str,
    yaml_path:str,
    target_config:str,
    output_path:str = None,
    valid_patterns:list[str] = 
        [   r"^eeg(_|$)",
            r"^accel(_|$)", r"^accelerometer(_|$)",
            r"^gyro(_|$)", r"^gyroscope(_|$)",
            r"^ppg(_|$)"
            r"^tele(_|$)", r"^telemetry(_|$)"
        ],
    mm_groupby_choice:str = "last"
):
    # Load configurations from yaml file
    presets = load_presets(yaml_path)
    if target_config not in presets:
        raise ValueError("Target configuration not found")

    # Handle the case the provided src path is a file
    if os.path.isfile(src_path):
        return convert_file(
            src_path,
            presets,
            target_config,
            output_path=output_path,
            mm_groupby_choice=mm_groupby_choice
        )
    # Handle the case the provided src path is a directory
    elif os.path.isdir(src_path):
        return convert_directory(
            src_path,
            presets,
            target_config,
            output_dir=output_path,
            valid_patterns=valid_patterns
        )
    # Ya dun goofed and provided an invalid input src path.
    else:
        raise ValueError("Invalid path")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Given either a single csv file or a directory, convert it to a different configuration type")
    parser.add_argument('query_src', help="Either a specific `.csv` file or directory", type=str)
    parser.add_argument('-cs', '--config_src', help="The path to the configuration yaml src (default='./record/stream_presets.yaml')", type=str, default="./record/stream_presets.yaml")
    parser.add_argument('-tc', '--target_config', help="The name of the configuration we want to convert to (default='bluemuse')", type=str, default='bluemuse')
    parser.add_argument('-gbc', '--groupby_choice', help="[ONLY FOR MIND MONITOR CONVERSIONS] Should we groupby and then use the last or first?", type=str, choices=['last','first','none'], default='last')
    args = parser.parse_args()
    convert_input(
        args.query_src,
        args.config_src,
        target_config=args.target_config,
        mm_groupby_choice=args.groupby_choice
    )