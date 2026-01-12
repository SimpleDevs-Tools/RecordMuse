import numpy as np
import pandas as pd
from scipy.signal import iirnotch, filtfilt, welch, butter
import matplotlib.pyplot as plt
import sys
import argparse
from pathlib import Path


# ===================== CONFIG =====================

FS = 256.0          # EEG sampling rate (Hz)
NOTCH_FREQ = 60.0   # Power line frequency (Hz)
NOTCH_Q = 25.0            # Quality factor (30–50 typical)

BANDPASS_LOW = 1.0        # Hz
BANDPASS_HIGH = 40.0      # Hz
BANDPASS_ORDER = 4

EEG_CHANNELS = ['TP9', 'AF7', 'AF8', 'TP10', 'Right AUX']


# ===================== NaN Interpolation =====================

def interpolate_nans(x):
    nans = np.isnan(x)
    if not nans.any():
        return x
    idx = np.arange(len(x))
    x[nans] = np.interp(idx[nans], idx[~nans], x[~nans])
    return x

# ===================== MAIN =====================

def filter_eeg(eeg_csv_path, apply_bandpass:bool=False, verbose:bool=True):

    # ===================== READING =====================
    
    eeg_csv_path = Path(eeg_csv_path)

    if not eeg_csv_path.exists():
        raise FileNotFoundError(f"File not found: {eeg_csv_path}")

    if verbose: print(f"Loading EEG file: {eeg_csv_path}")
    df = pd.read_csv(eeg_csv_path)
    
    # Check channels exist
    for ch in EEG_CHANNELS:
        if ch not in df.columns:
            raise ValueError(f"Missing EEG channel: {ch}")

    eeg_data = df[EEG_CHANNELS].values
    for ch in range(eeg_data.shape[1]):
        eeg_data[:, ch] = interpolate_nans(eeg_data[:, ch])
    if verbose:
        print("NaNs in raw EEG:", np.isnan(eeg_data).any())
        print("NaNs per channel:", np.isnan(eeg_data).sum(axis=0))
    
    # ===================== FILTER DESIGN =====================

    if verbose: print("Designing 60 Hz notch filter...")
    b_notch, a_notch = iirnotch(NOTCH_FREQ, NOTCH_Q, FS)

    if verbose: print("Designing bandpass filter (1–40 Hz)...")
    # Note: Butterworth filters are maximally flat and produce
    # smooth roll-off instead of a cliff, hard stop.
    b_bp, a_bp = butter(
        BANDPASS_ORDER,
        [BANDPASS_LOW, BANDPASS_HIGH],
        fs=FS,
        btype='band'
    )

    # ===================== APPLY FILTERS =====================

    if verbose: print("Applying notch filter (zero-phase)...")
    filtered = np.zeros_like(eeg_data)

    for ch in range(eeg_data.shape[1]):
        x = eeg_data[:, ch]
        # Remove DC offset / de-meaning (important before filtering & PSD)
        # Subtracting the mean removes:
        #   - Electrode DC offset
        #   - Slow amplifier bias
        #   - Improves numerical stability
        x = x - np.mean(x)
        # 1. Notch
        x = filtfilt(b_notch, a_notch, x)
        # 2. Bandpass, if prompted
        if apply_bandpass: 
            x = filtfilt(b_bp, a_bp, x)
        # 3. Save the filtered data into its column
        filtered[:, ch] = x

    # Save filtered file
    out_path = eeg_csv_path.with_name(
        eeg_csv_path.stem + "_filtered.csv"
    )

    df_filtered = df.copy()
    df_filtered[EEG_CHANNELS] = filtered
    df_filtered.to_csv(out_path, index=False)

    if verbose: print(f"Filtered EEG saved to: {out_path}")

    # ===================== OPTIONAL QC PLOT =====================

    if verbose: print("Plotting PSD (channel TP9) for verification...")
    f_raw, pxx_raw = welch(eeg_data[:, 0], FS, nperseg=1024)
    f_filt, pxx_filt = welch(filtered[:, 0], FS, nperseg=1024)

    plt.figure(figsize=(8, 4))
    plt.semilogy(f_raw, pxx_raw, label="Raw")
    plt.semilogy(f_filt, pxx_filt, label="60 Hz Notched")
    plt.xlim(0, 100)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Power")
    plt.title("EEG Power Spectral Density (TP9)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(eeg_csv_path.with_name(eeg_csv_path.stem + "_filtered.png"), bbox_inches='tight')
    plt.show()

    # Return the outpath
    return out_path


# ===================== ENTRY POINT =====================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Filters 60Hz notch with a provided EEG file outputted from `record.py`.")
    parser.add_argument('filepath', help="Provide the relative filepath to your raw EEG file.", type=str)
    parser.add_argument('-b', '--apply_bandpass', help="Should we apply bandpass filtering?", action="store_true")
    parser.add_argument('-v', '--verbose', help="Print statements to track how the operation is going?", action="store_true")
    args = parser.parse_args()
    filter_eeg(args.filepath, apply_bandpass=args.apply_bandpass, verbose=args.verbose)