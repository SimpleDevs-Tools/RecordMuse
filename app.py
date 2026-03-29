import streamlit as st
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from processing.convert import mm_to_bluemuse
from processing.filter import filter_eeg
from processing.normalize import normalize
from analysis.psd import calculate_psd

st.set_page_config(page_title="Record Muse", page_icon="📈")

# ================================
# UTILITY FUNCTIONS 
# ================================

def find_recording_dirs(
    root: Path,
    prefix: str = "_recording_",
    recursive: bool = True
):
    """Simply find directories and subdirectories with a provided prefix"""
    results = []
    # Choose iterator based on recursion flag
    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in iterator:
        if not path.is_dir(): 
            continue
        if prefix is not None and not path.name.startswith(prefix):
            continue
        stat = path.stat()
        created = datetime.fromtimestamp(stat.st_ctime)
        results.append({
            "name": path.name,
            "absolute_path": path,
            "relative_path": path.relative_to(root),
            "created": created,
        })
    return sorted(results, key=lambda x: x["created"], reverse=True)

def check_valid_dir_with_file(
    d, 
    filenames
):
    """Determine if a provided path contains the listed filenames"""
    base = Path(d)
    return all((base / f).is_file() for f in filenames)

def check_multiple_dirs_with_files(
    dirs, 
    filenames
):
    """Given a set of directories, confirm if they are valid by checking for filenames immediately within them."""
    filenames = set(filenames)
    ok, missing = [], []
    for rec in dirs:
        if check_valid_dir_with_file(rec['absolute_path'], filenames):
            ok.append(rec)
        else:
            missing.append(rec)
    return ok, missing


"""
# RecordMuse

A collection of Python packages for reading EEG, Accelerometer, Gyroscope, and 
PPG data from a **Muse S** or **Muse 2** devices by InteraXon Inc. This tool allows you to:

1. Recording LSL streams emitted by applications such as [BlueMuse](https://github.com/kowalej/BlueMuse), [Petal Metrics](https://petal.tech/downloads), and [Mind Monitor](https://mind-monitor.com/).
2. Perform basic plotting, duplicate record analysis, and format conversions.
"""

with st.expander("Prerequisite Software"):
    """
    _You must be running one of these Lab Streaming Layer (LSL) applications. This process assumes that you are running **Bluemuse**._
    """
    col1,col2,col3 = st.columns(3)
    with col1:
        st.markdown("**Bluemuse** (Windows) - RECOMMENDED!", width="stretch", text_alignment="center")
        st.link_button("Github Repo", "https://github.com/kowalej/BlueMuse", width="stretch")
    with col2:
        st.markdown("**Petal Metrics** (Windows, OS X, Linux)", width="stretch", text_alignment="center")
        st.link_button("Official Store", "https://petal.tech/downloads", width="stretch")
        st.link_button("_Free Versions_ (Windows, Linux only)", "https://drive.google.com/drive/folders/1pxSlfkkcTht9MzreAyp8IR23FEXUREAD?usp=sharing")
    with col3:
        st.markdown("Mind Monitor (Windows, OS X, iOS, Android)", width="stretch", text_alignment="center")
        st.link_button("Official Download", "https://mind-monitor.com/", width="stretch")

with st.expander("Data Formatting and Features: _BlueMuse_"):
    st.markdown("_BlueMuse_ does not have any file-saving functionality. You must use a separate application (e.g. _RecordMuse_) to record data.")
    st.markdown("There are **4** separate streams that _BlueMuse_ outputs and _RecordMuse_ records:")
    with st.expander("`Accelerometer.csv`"):
        """
        - unix_ms
        - lsl_unix_ts
        - X
        - Y
        - Z
        """
    with st.expander("`EEG.csv`"):
        """
        - unix_ms
        - lsl_unix_ts
        - TP9
        - AF7
        - AF8
        - TP10
        - Right AUX
        """
    with st.expander("`Gyroscope.csv`"):
        """
        - unix_ms
        - lsl_unix_ts
        - X
        - Y
        - Z
        """
    with st.expander("`PPG.csv`"):
        """
        - unix_ms
        - lsl_unix_ts
        - PPG1
        - PPG2
        - PPG3
        """
with st.expander("Data Formatting and Features: _Petal Metrics_"):
    st.markdown("Data logs are saved locally and are the recommended way to access data. If needed, you can use _RecordMuse_ to record the LSL streams outputted by _Petal Metrics_; however, some data logs may not be properly recorded.")
    with st.expander("`accelerometer.csv`"):
        """
        - id
        - lsl_ts
        - unix_ts
        - x
        - y
        - z
        """
    with st.expander("`eeg.csv`"):
        """
        - id
        - lsl_ts
        - unix_ts
        - ch1
        - ch2
        - ch3
        - ch4
        - ch5
        """
    with st.expander("`gyroscope.csv`"):
        """
        - id
        - lsl_ts
        - unix_ts
        - x
        - y
        - z
        """
    with st.expander("`ppg.csv`"):
        """
        - id
        - lsl_ts
        - unix_ts
        - ambient
        - ir
        - red
        """
    with st.expander("`telemetry.csv`"):
        """
        - id
        - lsl_ts
        - unix_ts
        - battery_level
        - temperature_c
        - fuel_gauge_voltage
        """
    with st.expander("`connection_status.csv`"):
        """
        - id
        - lsl_ts
        - unix_ts
        - status
        """
with st.expander("Data Formatting and Features: _Mind Monitor_"): 
    st.markdown("_Mind Monitor_ is a mobile app that is **INCOMPATIBLE** with _RecordMuse_. Instead, _Mind Monitor_ has the ability to save data logs by itself.")
    st.markdown("The Android version of _Mind Monitor_ gives you flexibility with where the outputted `.csv` file is saved. On iOS and iPad OS, you MUST connect a Dropbox account; all data logs are saved via the cloud, meaning your mobile device requires an internet connection.")
    st.error("**Warning**: We do NOT recommend _Mind Monitor_ as a data collection scheme. This is because the application will condense all data streams into a singular file. This in turn causes duplicates and other anomalies as the software attempts to merge timestamps and events. Furthermore, we expect that some time lag is present due to the application also performing bandpower calculations.")
    with st.expander("`mindMonitor_<datetime>.csv`"):
        """
        - TimeStamp
        - Delta_TP9, Delta_AF7, Delta_AF8, Delta_TP10
        - Theta_TP9, Theta_AF7, Theta_AF8, Theta_TP10
        - Alpha_TP9, Alpha_AF7, Alpha_AF8, Alpha_TP10
        - Beta_TP9, Beta_AF7, Beta_AF8, Beta_TP10
        - Gamma_TP9, Gamma_AF7, Gamma_AF8, Gamma_TP10
        - RAW_TP9, RAW_AF7, RAW_AF8, RAW_TP10
        - AUX_RIGHT, AUX_LEFT
        - Accelerometer_X, Accelerometer_Y, Accelerometer_Z
        - Gyro_X, Gyro_Y, Gyro_Z
        - PPG_Ambient, PPG_IR, PPG_Red, Heart_Rate
        - HeadBandOn, 
        - HSI_TP9, HSI_AF7, HSI_AF8, HSI_TP10,
        - Battery
        - Elements
        """


# ================================
# State Initialization
#   We store references to existing trials that match certain qualifications
#   Unique to this page, we also store a `proc` or "process" state that is referred to when demo-ing or recording EEG data.
# ================================
if "trials" not in st.session_state:    st.session_state.trials = []
if "selected" not in st.session_state:  st.session_state.selected = set()
if "proc" not in st.session_state:      st.session_state.proc = None
# --------------------------
# This is a unique helper function. It tells us if a process is running
# --------------------------
def is_running():
    p = st.session_state.proc
    return p is not None and p.poll() is None

"""
---

## Before You Begin: Modifying Preset Configurations

_RecordMuse_ requires a specific configuration file: `record/stream_presets.yaml`. This is a special file that contains the stream configurations for how 
_RecordMuse_ should record data from either _BlueMuse_ or _Petal Metrics_ (remember: _Mind Monitor_ does not actually interface with _RecordMuse_). 

Both `record/demo.py` and `record/record.py` rely on this `.yaml` file, and you can either 1) Modify this file to your liking, or 2) create your own 
configuration `.yaml` file. If you decide to create your own config file, then you must **modify `demo.py` and `record.py` to point to the new config file!** 

To debug whether the final config file is being properly read and cross-referenced with your LSL streaming software, then follow these steps:

1. Activate either your _BlueMuse_ or _Petal Metrics_ stream.
2. Run `record/stream_info.py`. You can modify it to point to your intended `.yaml` file.
3. In the Terminal window, check if there are any errors.

If your config file is being properly used, you should see details in the terminal window. If not, an error message may pop up.
"""


# ================================
# Interface #1: Demo-ing, Recording, and Converting
#   In the interface, we have 3 columns, each with unique functions.
#   1. DEMO the recording procedure. This invokes the `proc` state to check if the subprocess for it is running or not.
#   2. RECORD the EEG. This also uses the `proc` state and actually saves the recordings with a `_recording_` prefix
#   3. CONVERT recordings from Mind Monitor into the correct formatting, compatible wiht BlueMuse recordings.
#  ================================
col1, col2, col3 = st.columns(3)

# --------------------------
# Column 1: Demoing
# --------------------------
with col1:
    # Header and text description
    """
    ## Demo
    
    See if your BlueMuse system is working. This is **purely** for visualization and 
    debugging; it doesn't actually record.
    """
    # Interactable buttons
    if st.button("Run Demo Visualization", disabled=is_running()):
        st.session_state.proc = subprocess.Popen([sys.executable, "./record/demo.py"])
        st.rerun()
    if st.button("Stop Demo Visualization", disabled=not is_running()):
        st.session_state.proc.terminate()
        st.session_state.proc = None
        st.rerun()
        
# --------------------------
# Column 2: Recording
# --------------------------
with col2:
    # Header and text description
    """
    ## Record
    
    Record data using BlueMuse and your Muse device. For best results, follow 
    the default settings provided.
    """
    # Command line designations abd interactable fields
    arg1 = st.text_input(
        "Output directory", 
        value=None, 
        placeholder="Blank = datetime-stamped dir."
    )
    arg2 = st.number_input(
        "Recording duration (seconds)", 
        value=600, 
        placeholder="How long should the recording last (in seconds)?"
    )
    arg3 = st.checkbox(
        "Visualize streams", 
        value=False
    )
    # Interactable buttons
    if st.button("Start Recording", disabled=is_running()):
        args = [ sys.executable, "./record/record.py"]
        if arg1 is not None: args.extend(['-d', arg1])
        if arg2 is not None: args.extend(['-rd', str(arg2)])
        if arg3: args.append('-v')
        st.session_state.proc = subprocess.Popen(args)
        st.rerun()
    if st.button("Stop Recording", disabled=not is_running()):
        st.session_state.proc.terminate()  # SIGTERM
        st.session_state.proc = None
        st.rerun()

# --------------------------
# Column 3: Converting
# --------------------------
with col3:
    # Header and text description
    """
    ## Convert
    
    Convert from Mind Monitor's formating to BlueMuse's format. _Timestamps may not 
    properly convert._", help="Mind Monitor condenses all recordings into a single 
    row, including EEG, IMU, and Heart Rate. Consequently, many rows may share the 
    same timestamp. This system will try its best to account for this, but you'll 
    likely only get the last recording per timestamp group.
    """
    # Command line designations and interactable fields
    arg1 = st.text_input(
        "EEG file from Mind Monitor.", 
        value=None
    )
    arg2 = st.text_input(
        "Output directory name (optional)", 
        value=None, 
        placeholder="Blank = automatically generated"
    )
    arg3 = st.selectbox(
        "Timestamp Group Candidate Selection", 
        options=['Last','First']
    )
    # Interactable buttons
    if st.button("Convert"):
        output_dir, eeg_outpath, accel_outpath, gyro_outpath, blinks_outpath = mm_to_bluemuse(arg1, output_dir=arg2, groupby_choice=arg3.lower())
        st.markdown(f"Converted files saved within `{output_dir}`")


# ================================
# Interface #2: Pre-Processing EEG
#   Assuming that you use the tools above to record and/or convert your EEG 
#   data into a usable format, we can now pre-process the EEG. To do this, 
#   we need an interface (just a form) to identify viable trials with.
# ================================

"""
---

## Pre-process EEG

All recordings are identified with a prefix `_recording_` to them. You can use 
this tool to check how many have been identified. You can also control under 
which root directory you want to check under, if needed.

Regardless, the current task is to, for each trial with rest EEG and simulation 
EEG, normalize the data for PSD analysis. _**You must manually move your group 
of recordings into a single folder. So for example, if you recorded a resting-state 
EEG recording and a simulation-state EEG recording for a single person, then you 
must arrange them similarly to what's visually depicted below. This participant's 
directory must be stored within a parent directory in of itself.**_

```
./
└── samples/
    ├── participant_id/
    │   ├── _recording_rest/
    │   │   ├── EEG.csv
    │   │   └── ...
    │   └── _recording_vr/
    │       ├── EEG.csv
    │       └── ...
    └── ...
```
"""

# --------------------------
# Interactive fields.
# --------------------------
root_dir = st.text_input(
    "Root directory to scan", 
    value="samples"
)
col1, col2 = st.columns(2)
with col1:
    rest_eeg_src = st.text_input(
        "Rest EEG filepath", 
        value='_recording_rest/EEG.csv', 
        help="_Filepath (relative to the directory of each **trial**) to the EEG file representing the rest-state EEG_"
    )
with col2:
    sim_eeg_src = st.text_input(
        "Simulation EEG filepath", 
        value='_recording_vr/EEG.csv', 
        help="_Filepath (relative to the directory of each **trial**) to the EEG file representing the simulation EEG_"
    )
# --------------------------
# Interactive button
# --------------------------  
if st.button("Scan for Trials", width="stretch"):
    root = Path(root_dir).resolve()
    if not root.exists():
        st.error("Directory does not exist")
    else:
        st.session_state.trials = find_recording_dirs(root, prefix=None, recursive=False)
        st.session_state.selected.clear()

# ================================
# Interaction #3: Selecting files, then post-processing them.
#   We need an interface that does several things. Namely:
#   1. Checking for the trials that actually contain the designated rest and simulation EEG files
#   2. Filtering the signal data for both the rest and EEG data
#   3. Normalizing the simulation data based on the EEG data
#   4. Calculating the PSDs based on the normalized data
# ================================
trials = st.session_state.trials
if not trials: 
    st.info("No trial directories found.")
else:
    # Initially check - how many are valid, and how many are invalid?
    valid, invalid = check_multiple_dirs_with_files(trials, [rest_eeg_src, sim_eeg_src])
    # If we don't have any valids, then it's bust
    if len(valid) == 0:
        st.info(f"Found {len(trials)} trial(s) [{len(valid)}/{len(trials)} successful matches]")
    # We found at least one valid trial
    else:
        st.success(f"Found {len(trials)} trial(s) [{len(valid)}/{len(trials)} successful matches]")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("_Trials that contain both rest and simulation EEG:_")
            if len(valid) == 0:
                st.info("No valid trials! Double-check your data!")
            else:
                for trial in valid:
                    name = trial['name']
                    key = trial["relative_path"]
                    created = trial['created'].strftime('%Y-%m-%d %H:%M:%S')
                    checked = st.checkbox(
                        f"📁 {name}  (`{key}` - {created})",
                        key=f"chk_{key}",
                        value=key in st.session_state.selected,
                    )
                    if checked: st.session_state.selected.add(key)
                    else:       st.session_state.selected.discard(key)
        with col2:
            st.markdown("_Trials that are missing one or both EEG recordings:_")
            if len(invalid) == 0:
                st.info("No invalid trials! Congratulations!")
            else:
                for trial in invalid:
                    name = trial['name']
                    key = trial["relative_path"]
                    created = trial['created'].strftime('%Y-%m-%d %H:%M:%S')
                    st.checkbox(
                        f"📁 {name}  (`{key}` - {created})",
                        key=f"chk_{key}",
                        value=key in st.session_state.selected,
                        disabled=True
                    )
# --------------------------
# Actual operations for pre-processing EEG data
# --------------------------
if len(st.session_state.selected) > 0:
    selected = [
        t for t in st.session_state.trials 
        if t['relative_path'] in st.session_state.selected
    ]
    # --------------------------
    # Explanation Text
    # --------------------------
    st.divider()
    st.markdown(
        "When you click the following button, these operations will occur in order:\n" + \
        "1. **Filter** the signal data for both the rest and EEG data\n" + \
        "2. **Normalize** the simulation data based on the EEG data\n" + \
        "3. **Calculate** the PSDs based on the normalized data"
    )
    # --------------------------
    # Interactive fields
    # --------------------------
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Filtering Params")
        st.markdown("This operation generates a new `EEG_filtered.csv` for each of the rest and simulation eeg files.")
        #filter_outpath = st.text_input()
        apply_bandpass = st.checkbox("Apply bandpass filtering to smooth EEG signals", value=True)
    with col2:
        st.subheader("Normalization Params")
        timestamp_colname = st.text_input("Timestamp column name", value='lsl_unix_ts')
        col2a, col2b = st.columns(2)
        with col2a:     start_buffer = st.number_input("Start buffer", value=5.0, help="The amount of time at the start that is ignored; the time scale is dependent on if your timestamp column is in seconds, milliseconds, or other.")
        with col2b:     end_buffer = st.number_input("End buffer", value=5.0, help="The amount of time at the end that is ignored; the time scale is dependent on your timestamp column's time scale.")
        validate_normalization = st.checkbox("Validate via command line", help="Make sure you have access to the command line if you select this.")
    # --------------------------
    # Interactive button
    # --------------------------
    if st.button(f"Pre-process EEG for selected trials ({len(selected)} trials)", width="stretch"):
        # We begin operations. We add a progress bar for better visualization of the process
        progress_bar = st.progress(0, text="Pre-processing EEG...")
        # Loop through each selected trial
        for index in range(len(selected)):
            trial = selected[index]
            name = trial['name']
            path = trial['absolute_path']
            progress_bar.progress(
                int(index/len(selected) * 100),
                text=f"Pre-processing EEG... | {str(path)}"
            )
            # First op: filtering
            progress_bar.progress(
                int(index/len(selected) * 100),
                text=f"Pre-processing EEG... | {str(path)} | Rest EEG Filtering"
            )
            eeg_rest_filtered_src = filter_eeg(str(path / rest_eeg_src), apply_bandpass=apply_bandpass)
            progress_bar.progress(
                int(index/len(selected) * 100),
                text=f"Pre-processing EEG... | {str(path)} | Simulation EEG Filtering"
            )
            eeg_sim_filtered_src = filter_eeg(str(path / sim_eeg_src), apply_bandpass=apply_bandpass)
            # Second op: normalization
            progress_bar.progress(
                int(index/len(selected) * 100),
                text=f"Pre-processing EEG... | {str(path)} | Normalization"
            )
            eeg_normalized_src = normalize(
                str(path / eeg_rest_filtered_src), 
                str(path / eeg_sim_filtered_src), 
                ts_col=timestamp_colname, 
                start_buffer=start_buffer, 
                end_buffer=end_buffer,
                validate=validate_normalization
            )
            progress_bar.progress(
                int(index/len(selected) * 100),
                text=f"Pre-processing EEG... | {str(path)} | PSD Calculation"
            )
            # Third op: PSD Calculation
            calculate_psd(str(path / eeg_normalized_src))
            # Close off with progresss report
            progress_bar.progress(
                int((index+1)/len(selected) * 100),
                text=f"Pre-processing EEG... | {str(path)} Complete!"
            )
        # Complete the progress bar
        progress_bar.progress(100, text="Completed Pre-processing EEG!")


# ================================
# Command Lines: For running the operations via command line
# ================================
st.divider()
st.header("Command Line Equivalents")
st.markdown(
    "If you want to run these commands via the command line, " + \
    "then here are the list of commands."
)
# --------------------------
# Interaction #1: Demo, Record, and Convert
# --------------------------
with st.expander("### Demo, Record, or Convert EEG"):
    st.code(
        "# Debug Stream, Identify Optimal Preset Config:\n" + \
        "python ./record/stream_info.py\n" + \
        "# Demo:\n" + \
        "python ./record/demo.py\n" + \
        "# Record EEG via BlueMuse:\n" + \
        "python ./record/record.py [-d <OUTPUT_DIR>]\n" + \
        "# Convert:\n" + \
        "python ./processing/convert.py [path to eeg file]", 
        language="bash"
    )
# --------------------------
# Interaction #2: Pre-process EEG
# --------------------------
with st.expander("### Pre-processing EEG"):
    st.code(
        "# Filter EEG:\n" + \
        "python ./processing/filter.py [path to your rest or vr eeg `.csv`] -b -v\n" + \
        "# Normalize EEG:\n" + \
        "python ./processing/normalize.py [path to rest EEG] [path to VR eeg] [-tc] [-sb] [-eb] [-v]\n" + \
        "# Calculate PSD and bandpowers:\n" + \
        "python ./analysis/psd.py [path to filtered, normalized EEG]\n" + \
        "# Validate via Plotting:\n" + \
        "python ./analysis/validate.py <path/to/directory> [-tc <timestamp/column/name>] [-p]", 
        language="bash"
    )