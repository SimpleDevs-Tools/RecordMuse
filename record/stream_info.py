from pylsl import resolve_streams
import yaml
import pprint
import argparse

# ============================
# Normalization Between Configurations
# ============================

TYPE_ALIASES = {
    "accel": "accelerometer",
    "accelerometer": "accelerometer",
    "gyro": "gyroscope",
    "gyroscope": "gyroscope",
    "eeg": "eeg",
    "ppg": "ppg",
    "tele": "telemetry",
    "binaryconnectionstatus": "connection_status",
}
def normalize(s):
    return s.lower().replace(" ", "").replace("_", "")
def normalize_type(t):
    return TYPE_ALIASES.get(normalize(t), normalize(t))


# ============================
# Getter Functions
# ============================

def get_presets(src:str = "record/stream_presets.yaml"):
    stream_presets = None
    with open(src) as stream:
        try:
            stream_presets = dict(yaml.safe_load(stream))
        except yaml.YAMLError as exc:
            print(exc)
    return stream_presets

def get_streams(verbose:bool = True):
    # Discover all active streams
    streams = resolve_streams(wait_time=3)
    # Extract and print the names of all discovered streams
    stream_details = []
    if verbose:
        print("")
        print("=== DETECTED STREAM DETAILS ===")
    for i, stream in enumerate(streams):
        if verbose:
            print(f"Stream `{i+1}`:")
            print(f"  Name: {stream.name()}")
            print(f"  Type: {stream.type()}")
            print(f"  Channels: {stream.channel_count()}")
            print(f"  Sampling Rate: {stream.nominal_srate()}")
            print(f"  Source ID: {stream.source_id()}")
            print(f"  Host: {stream.hostname()}")
        stream_details.append({
            "name": stream.name(),
            "type": stream.type(),
            "channels": stream.channel_count(),
            "sample_rate": stream.nominal_srate(),
            "info": stream
        })
    # return streams
    return stream_details


# ============================
# Scoring functions
# ============================

def is_match(preset_stream, actual_stream):
    return (
        normalize_type(preset_stream["type"]) == normalize_type(actual_stream["type"])
        and len(preset_stream["channels"]) == actual_stream["channels"]
    )

def score_stream_match(preset_stream, actual_stream):
    score = 0
    # Normalize preset stream
    p_type = normalize_type(preset_stream["type"])
    # Normalize actual stream
    a_type = normalize_type(actual_stream["type"])
    
    #  Similarity Scoring:
    # --- Type match: strong
    if p_type == a_type:    score += 5
    # --- Channel count: strong
    expected_channels = len(preset_stream.get("channels", []))
    actual_channels = actual_stream["channels"]
    if expected_channels == actual_channels:                score += 2
    elif abs(expected_channels - actual_channels) <= 1:     score += 1
    # --- Sample rate similarity
    if "sample_rate" in preset_stream:
        expected_sr = preset_stream["sample_rate"]
        actual_sr = actual_stream["sample_rate"]
        print(type(expected_sr), expected_sr, type(actual_sr), actual_sr)
        if actual_sr > 0:
            diff = abs(expected_sr - actual_sr)
            if diff < 1:    score += 2
            elif diff < 10: score += 1
    # Return score
    return score

# ----------------------------
# Main matching functions
# ----------------------------

def combine_stream(preset_stream, actual_stream):
    return {
        "name": preset_stream.get("name") or actual_stream["name"],
        "type": actual_stream["type"],  # always trust actual
        "channels": preset_stream["channels"],  # always from preset
        "sample_rate": preset_stream.get("sample_rate") or actual_stream["sample_rate"],
    }
def match_preset(preset_streams, actual_streams):
    matched = []
    used_indices = set()
    for p_stream in preset_streams:
        for i, a_stream in enumerate(actual_streams):
            if i in used_indices:   
                continue
            if is_match(p_stream, a_stream):
                matched.append(combine_stream(p_stream, a_stream))
                used_indices.add(i)
                break  # move to next preset stream
    return matched
def get_best_stream_preset(presets_src:str="record/stream_presets.yaml"):
    presets = get_presets(src = presets_src)
    streams = get_streams()
    # Assertions for validity check - no NONE data
    assert presets is not None, "No presets provided"
    assert streams is not None and len(streams)>0, "No streams provided"
    # Start to compare each preset to find the best matched preset config.
    results = {}
    for preset_name, preset_streams in presets.items():
        # Each preset has a list of streams. So we need to get all matched streams.
        matched_streams = match_preset(preset_streams, streams)
        # We calculate the "match" score that quantifies how much the current, actual stream matches each preset config.
        score = len(matched_streams)
        coverage = score / len(preset_streams)
        results[preset_name] = {
            "matched": matched_streams,
            "score": score,
            "coverage": coverage,
        }
    # Select best preset
    best = max(
        results.items(),
        key=lambda x: (x[1]["score"], x[1]["coverage"])
    )
    return best[0], results[best[0]]['matched'], results

if __name__ == "__main__":
    # Handle command line arguments
    parser = argparse.ArgumentParser(description="Check what data streams an active LSL software is outputting, and contrast that with known presets.")
    parser.add_argument("-c", "--config_filepath", help="Path to the query `.yaml` configuration file. Default=`record/stream_presets.yaml`.", type=str, default='./record/stream_presets.yaml')
    args = parser.parse_args()

    # Get the best preset and best stream config
    best_preset, best_streams, _ = get_best_stream_preset(presets_src=args.config_filepath)

    # Print results    
    print("")
    print("=== Estimated Stream Preset ===")
    print("- Best Preset:", best_preset)
    print("- Best Preset Config:")
    pprint.pprint(best_streams, indent=2)
    print("")
