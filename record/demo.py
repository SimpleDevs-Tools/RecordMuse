import time
import signal
from threading import Thread, Event, Lock
from collections import deque

import numpy as np
from pylsl import StreamInlet, resolve_byprop

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets


# ===================== CONFIG =====================

STREAM_TYPES = ['EEG', 'Accelerometer', 'Gyroscope', 'PPG']

STREAM_CHANNELS = {
    'EEG': ['TP9', 'AF7', 'AF8', 'TP10', 'Right AUX'],
    'Accelerometer': ['X', 'Y', 'Z'],
    'Gyroscope': ['X', 'Y', 'Z'],
    'PPG': ['PPG1', 'PPG2', 'PPG3']
}

STREAM_RATES = {
    'EEG': 256,
    'Accelerometer': 50,
    'Gyroscope': 50,
    'PPG': 64
}

VIS_WINDOW_SEC = 5
PLOT_FPS = 20


# ===================== GLOBALS =====================

stop_event = Event()

viz_buffers = {}
viz_locks = {}

for stype in STREAM_TYPES:
    maxlen = VIS_WINDOW_SEC * STREAM_RATES[stype]
    viz_buffers[stype] = deque(maxlen=maxlen)
    viz_locks[stype] = Lock()


# ===================== PRODUCER =====================

def producer_thread(stream_type):
    print(f"Searching for {stream_type} stream...")
    streams = resolve_byprop('type', stream_type, timeout=10.0)

    if not streams:
        print(f"ERROR: {stream_type} stream not found.")
        return

    inlet = StreamInlet(streams[0])
    print(f"Visualizing {stream_type}")

    while not stop_event.is_set():
        sample, _ = inlet.pull_sample(timeout=1.0)
        if sample is None:
            continue

        with viz_locks[stream_type]:
            viz_buffers[stream_type].append(sample)


# ===================== VISUALIZATION =====================

class StreamWindow(QtWidgets.QWidget):
    def __init__(self, stream_type):
        super().__init__()
        self.stream_type = stream_type
        self.channels = STREAM_CHANNELS[stream_type]
        self.n_ch = len(self.channels)

        self.setWindowTitle(stream_type)
        self.resize(800, 400)

        layout = QtWidgets.QVBoxLayout(self)

        self.plot = pg.PlotWidget()
        self.plot.showGrid(x=True, y=True)
        self.plot.addLegend()
        layout.addWidget(self.plot)

        self.curves = []
        for i, ch in enumerate(self.channels):
            curve = self.plot.plot(
                pen=pg.intColor(i),
                name=ch
            )
            self.curves.append(curve)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(int(1000 / PLOT_FPS))

    def update_plot(self):
        with viz_locks[self.stream_type]:
            data = np.array(viz_buffers[self.stream_type])

        if data.size == 0:
            return

        x = np.arange(len(data))
        for ch in range(self.n_ch):
            self.curves[ch].setData(x, data[:, ch])


class EEGWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.channels = STREAM_CHANNELS['EEG']
        self.n_ch = len(self.channels)

        self.setWindowTitle("EEG")
        self.resize(900, 600)

        layout = QtWidgets.QVBoxLayout(self)

        self.graphics = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics)

        self.plots = []
        self.curves = []

        for i, ch in enumerate(self.channels):
            p = self.graphics.addPlot(row=i, col=0)
            p.showGrid(x=True, y=True)
            p.setLabel('left', ch)

            if i > 0:
                p.setXLink(self.plots[0])

            curve = p.plot(pen='c')
            self.plots.append(p)
            self.curves.append(curve)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(int(1000 / PLOT_FPS))

    def update_plot(self):
        with viz_locks['EEG']:
            data = np.array(viz_buffers['EEG'])

        if data.size == 0:
            return

        x = np.arange(len(data))
        for ch in range(self.n_ch):
            self.curves[ch].setData(x, data[:, ch])


# ===================== SIGNAL HANDLING =====================

def handle_sigint(sig, frame):
    print("\nCtrl+C detected — exiting demo...")
    stop_event.set()
    QtWidgets.QApplication.quit()


# ===================== MAIN =====================

def demo():
    threads = []

    for stype in STREAM_TYPES:
        t = Thread(target=producer_thread, args=(stype,), daemon=True)
        t.start()
        threads.append(t)

    app = QtWidgets.QApplication([])

    signal.signal(signal.SIGINT, handle_sigint)

    # Let Python process signals while Qt runs
    sig_timer = QtCore.QTimer()
    sig_timer.start(100)
    sig_timer.timeout.connect(lambda: None)

    windows = []

    windows.append(EEGWindow())
    windows[-1].show()

    for stype in ['Accelerometer', 'Gyroscope', 'PPG']:
        w = StreamWindow(stype)
        w.show()
        windows.append(w)

    try:
        app.exec()
    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=2)
        print("Demo session closed.")


if __name__ == "__main__":
    demo()