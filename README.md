# Record Muse

A collection of Python packages for reading EEG, Accelerometer, Gyroscope, and PPG data from a Muse S or Muse 2 devices by InteraXon Inc. This tool allows you to:

1. Recording LSL streams emitted by applications such as [BlueMuse](https://github.com/kowalej/BlueMuse), [Petal Metrics](https://petal.tech/downloads), and [Mind Monitor](https://mind-monitor.com/).
2. Perform basic plotting, duplicate record analysis, and format conversions.

## Functions

### Demo-ing: `demo.py`

```bash
python src/demo.py
```

This script allows you to visualize the data streams _without recording data_ - hence, it's purely a demo operation. For recording, check out the next function: `record.py`.

![Recording Visualizations](./docs/record.png)

_**NOTE**: It is NOT safe to call this script BEFORE you start your LSL stream. I recommend running this script only AFTER your LSL stream is already on._

---

### Recording: `record.py`

```bash
python src/record.py [-d <OUTPUT_DIR>]
```

This script records the EEG, Accelerometer, Gyroscope, and PPG data simultaneously and outputs the streams as CSV files. It's multi-threaded (meaning that stream sampling and file saving are separate threads). It also provides visualizations of the current streams, similar to `demo.py`.

_**NOTE**: This script auto-generates an output directory, but if you want you can declare your own output directory via the optional argument `-d`. If a directory already exists with the same name, it appends a number system to the inputted directory and increments until a duplicate directory is no longer detected._

_**NOTE**: It is NOT safe to call this script BEFORE you start your LSL stream. I recommend running this script only AFTER your LSL stream is already on._

---

### Filtering: `filter.py`

```bash
python src/filter.py <path/to/eeg.csv> [-b]
```

This script looks at the EEG file generated from `src/record.py` and applies a 60Hz notch filter. This 60Hz notch filter is needed to counteract impedence caused by electrical components in the Muse device. This script can also apply a bandpass filter from 1-40Hz as a way to offset incredibly high Gamma frequencies. This can be toggled by adding a `-b` flag to your command.

To validate whether the operation was successful, a plot is generated and saved that lets you look at the Power Spectral Density (PSD) of the TP9 signal both before and after the filtering. You should see something similar to that shown below:

![docs/filtered.png](./docs/filtered.png)

_**NOTE**: You do not need to run this while you are recording. In fact, you're expected to run this immediately after recording your Muse data._

---

### Power Spectral Density: `src/psd.py`

```bash
python ./src/psd.py <path/to/eeg.csv>
```

This script calculates the PSD and bandpowers of a given EEG csv file. It's recommended to use EEG data that has at least been filtered by `filter.py`.

![Power Spectral Density](./docs/psd.png)
![Bandpowers](./docs/bandpowers.png)

_**NOTE**: This script will REMOVE YOUR ORIGINAL TIMESTAMPS and replace it with a relative `time` column. So if you have any time-based analysis, make sure to properly crop your EEG data time-wise prior to running this operations!_

## Installation

### Step 1: Set up an LSL stream

There are some options out there for you, sorted in descending recommendation:

1. [**BlueMuse**](https://github.com/kowalej/BlueMuse): The _recommended_ way of outputting an LSL stream of Muse data.
2. [Mind Monitor](https://mind-monitor.com/): An all-in-one package that also provides in-built recording functions, though timestamp accuracy is restricted.
3. [Petal Metrics](https://petal.tech/downloads): A viable alternative that also provides in-built recording, though with many caveats such as recording pausing when an EEG channel is interrupted.

Here are the basic rundowns of their functions:

|Application|LSL Stream Output|In-Built Recording|Requires Payment|Caveats|
|:-:|:-:|:-:|:-:|:-|
|**BluseMuse**|:ballot_box_with_check:|:x:|:x:|No in-built recording|
|Mind Monitor|:ballot_box_with_check:|:ballot_box_with_check:|:dollar:|Timestamps are packaged and lossy|
|Petal Metrics|:ballot_box_with_check:|:ballot_box_with_check:|:dollar:|Stops recording when signals are interrupted|

_This assumes that you are using **BlueMuse** for your LSL stream setup._

### Step 2: Install a virtual environment and dependencies

All dependencies are provided in `requirements.txt`. It's safest to set up a virtual Python environment first. This has been tested in Python `3.11`.

```bash
# Virtual environment `.venv` setup
py -m venv .venv
.venv/Scripts/activate      # Windows
source .venv/bin/activate   # Mac / Linux

# Installing dependencies via pip
pip install -r requirements.txt

# Commands (covered above)
# ...

# Closing the virtual environment
deactivate
```

### Step 3: Record

This is a two-step process:

1. Start streaming from whichever streaming application you've decided on.
2. Start recording via `src/record.py`
3. Do whatever task or operation you want while recording
4. After ceasing recording, run `src/filter.py` to perform a basic 60Hz notch filter, as well as 1-40Hz bandpass if you so choose.
5. Perform whatever operations needed to slice the EEG, Accelerometer, Gyroscope, and PPG data time-wise (i.e. align your data prior).
6. use `src/psd.py` to calculate the power spectral density (PSD) and time-series Bandpowers of your filtered, sliced EEG data.