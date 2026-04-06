import os
import yaml
import re
import pandas as pd
from collections import defaultdict
import argparse

# -------------------------
# Helpers
# -------------------------

def load_presets(
    yaml_path: str
) -> dict:
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def normalize(
    name: str
) -> str:
    return name.lower().replace(" ", "").replace("_", "")


def score_stream(
    csv_cols, 
    stream_config
):
    expected = set(map(normalize, stream_config["channels"]))
    actual = set(map(normalize, csv_cols))

    overlap = len(expected & actual)
    total = len(expected)

    return overlap / total if total > 0 else 0


def match_single_csv(
    df: pd.DataFrame, 
    presets: dict
):
    """
    Returns best (config, stream) match for ONE csv
    """
    csv_cols = df.columns

    best_match = None
    best_score = -1

    for config_name, streams in presets.items():
        for stream in streams:
            s = score_stream(csv_cols, stream)

            if s > best_score:
                best_score = s
                best_match = {
                    "config": config_name,
                    "name": stream["name"],
                    "type": stream["type"],
                    "score": s
                }

    return best_match


def match_directory(
    dir_path: str, 
    presets: dict,
    valid_patterns: list[str] = 
        [   r"^eeg(_|$)",
            r"^accel(_|$)", r"^accelerometer(_|$)",
            r"^gyro(_|$)", r"^gyroscope(_|$)",
            r"^ppg(_|$)"
            r"^tele(_|$)", r"^telemetry(_|$)"
        ]
):
    """
    Returns best config match across ALL csv files
    """
    config_scores = defaultdict(float)
    valid_files = 0

    # Compile regex patterns once
    compiled_patterns = None
    if valid_patterns:
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in valid_patterns]

    for f in os.listdir(dir_path):
        if not f.endswith(".csv"):
            continue

        name_no_ext = os.path.splitext(f)[0]
        if compiled_patterns:
            if not any(p.search(name_no_ext) for p in compiled_patterns):
                continue

        full_path = os.path.join(dir_path, f)
        df = pd.read_csv(full_path)

        match = match_single_csv(df, presets)

        if not match:
            continue

        config_scores[match["config"]] += match["score"]
        valid_files += 1

    if valid_files == 0:
        return None

    # Normalize scores
    for k in config_scores:
        config_scores[k] /= valid_files

    best_config = max(config_scores.items(), key=lambda x: x[1])[0]

    return best_config


# -------------------------
# Main entry point
# -------------------------

def get_config_type(path: str, yaml_path: str):
    presets = load_presets(yaml_path)

    if os.path.isfile(path):
        df = pd.read_csv(path)
        match = match_single_csv(df, presets)

        if match:
            return {
                "match config": match["config"],
                "match name": match["name"],
                "match type": match["type"]
            }
        return None

    elif os.path.isdir(path):
        best_config = match_directory(path, presets)

        if best_config:
            return {
                "match config": best_config
            }
        return None

    else:
        raise ValueError(f"Invalid path: {path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Identify which streaming configuration (BlueMuse, Petal Metrics, or Mind Monitor) your raw data best aligns with.")
    parser.add_argument('query_src', help="Either a specific `.csv` file or directory", type=str)
    parser.add_argument('-cs', '--config_src', help="The path to the configuration yaml src (default='./record/stream_presets.yaml')", type=str, default="./record/stream_presets.yaml")
    args = parser.parse_args()
    match = get_config_type(
        args.query_src, 
        args.config_src
    )
    print(match)