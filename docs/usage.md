# RecordMuse - Usage Guide

## Installation

### 1. Prerequisite Software

You must be running one of these Lab Streaming Layer (LSL) applications. This process assumes that you are running **Bluemuse**, but two alternatives are also suggested:

|App|OS|Download|LSL|Recording|Paywall|Notes|
|:-:|:-:|:--|:-:|:-:|:-:|:-|
|**BluseMuse**|Windows|[Github](https://github.com/kowalej/BlueMuse)|:ballot_box_with_check:|:x:|:x:|No in-built recording|
|Petal Metrics|Windows, OS X, Linux|[Website](https://petal.tech/downloads), [_Free Ver._$^1$](https://drive.google.com/drive/folders/1pxSlfkkcTht9MzreAyp8IR23FEXUREAD?usp=sharing) (Windows, Linux only)|:ballot_box_with_check:|:ballot_box_with_check:|:dollar:|Stops recording when signals are interrupted|
|Mind Monitor|iOS, Android|[Website](https://mind-monitor.com/)|:shrug:$^2$|:ballot_box_with_check:|:dollar:|Timestamps are packaged and lossy|

> **1:** Version 1.8.0 of the software has been cached prior to the developers paywalling their application. I've only managed to cache the Windows and Linux versions; I unfortunately no longer have access to the OS X version.
> **2:** I haven't explored this possibility yet. The _Mind Monitor_ application implies to allow streaming to a specific IP address and port, but preliminary exploration did not give me a chance to access this IP from another device on the same network.

### 2. Cloning the Repo

The easiest way to download this repo is to download the source code of our latest [release](https://github.com/SimpleDevs-Tools/RecordMuse/releases).

Alternatively, you can simply clone the repository via Git commands. This allows you to pull updates when needed. Just be sure to keep an eye out when we update new releases.

```bash
# HTTPS
https://github.com/SimpleDevs-Tools/RecordMuse.git
# SSH
git clone git@github.com:SimpleDevs-Tools/RecordMuse.git
```


### 3. Virtual Environment Setup

All dependencies are provided in `requirements.txt`. It's safest to set up a virtual Python environment first. This has been tested in Python `3.11`.

```bash
# Virtual environment `.venv` setup (Windows)
py -m venv .venv
.venv/Scripts/activate
# Virtual environment `.venv` setup (Mac / Linux)
python -m venv .venv
source .venv/bin/activate

# Installing dependencies via pip
pip install -r requirements.txt

# Do your thing
# <run commands here>
# Or run the Streamlit app to have a visual interface
streamlit run app.py

# Closing the virtual environment
deactivate
```

#### WARNING: Execution Policy and Permissions

If you attempt to activate your virtual environment and you get an error, then you need to double-check that you have execution policy permissions allowed.

Firstly, open up a PowerShell window in Administrator Mode. Then, double-check the output of this command. You are likely to see the following:

```bash
# Run this Command
Get-ExecutionPolicy -List

# Likely Output
Scope ExecutionPolicy
----- ---------------
MachinePolicy       Undefined
   UserPolicy       Undefined
      Process       Undefined
  CurrentUser       Undefined   # <-- This should be "RemoteSigned", but it isn't...
 LocalMachine    RemoteSigned
```

To change this, run the following command:

```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

You can double-check once more if the permission has been applied to "CurrentUser" - if so, then you're golden.

## Usage

All scripts are split between different directories:

- `record/`: contains all scripts related to demo-ing and recording EEG data.
- `processing/`: contains all scripts related to converting from _Mind Monitor_ to _BlueMuse_ formatting, filtering, and data normalization.
- `analysis/`: contains all scripts related to analysis, such as data validation and power spectral density (PSD) calculation.

### Option 1: Running with a User Interface

If you prefer a user interface for easy operation, you can run this repo as a Streamlit application:

```bash
streamlit run app.py
```

This interface gives you some basic controls for demo-ing, recording, converting, and processing EEG data. However, _not all functions are provided_. For more specific coverage, move onto **Option 2**.

### Option 2: Command-Line Interface

A quick run-through of operations may look something like this:

1. Record your Data
    1. Start your LSL streaming softare (_BlueMuse_ or _Petal Metrics_)
    2. Check if _RecordMuse_ properly detects which **streaming presets** are needed (`record/stream_info.py` and `record/stream_presets.yaml`)
    3. **Demo** your EEG data streams to ensure proper alignment with the user's scalp (`record/demo.py`)
    4. **Record** your EEG data (`record/record.py`)
2. Processing your Data
    1. (If needed) **Convert** your EEG data from _Mind Monitor_'s formatting to _BlueMuse_'s formatting (`processing/convert.py`)
    2. **Filter** your EEG data via a notch filter of 60Hz to remove noise from electrical components; apply an additional butterworth filter to further restrict high-frequency noise data (`processing/filter.py`)
    3. (0If you recorded rest-state EEG) **Normalize** your EEG samples (`processing/normalize.py`)
3. Analyze your Data
    1. Perform a Power Spectral Density calculation to identify key frequencies in your data (`analysis/psd.py`)
    2. Validate your samples (`analysis/validate.py`)

For more details on implementation specifics (e.g. command line flags, implementation details and methods), please refer to [methodology.md](./methodology.md).