import sys
import numpy as np
import serial
import time
import threading
import csv
from collections import deque
import pywt
from scipy import signal
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPen
from PyQt6.QtCore import Qt
from pyqtgraph import PlotWidget, mkPen
import pandas as pd

nomeArq = "Teste.csv"

esp = serial.Serial(
    port='COM3',
    baudrate=115200,
)

max_data_points = 4000  # Sliding window size
dados = deque(maxlen=max_data_points)
timestamp = deque(maxlen=max_data_points)
save_dados = []
save_timestamp = []
fs = 1000
onsets_wavelet = []
onsets_moving_avg = []

lock = threading.Lock()  # Avoid competition


def detect_onsets_wavelet(signal_data, fs=1000, refractory_period=0.5):
    widths = np.arange(1, 10)
    wavelet_coeffs, _ = pywt.cwt(signal_data, widths, 'mexh')
    wavelet_power = np.abs(wavelet_coeffs).sum(axis=0)
    threshold = np.mean(wavelet_power) + 2 * np.std(wavelet_power)
    detected_indices = np.where(wavelet_power > threshold)[0]

    final_onsets = []
    last_onset_time = -np.inf

    for idx in detected_indices:
        onset_time = idx / fs  # Time to seconds
        if onset_time - last_onset_time > refractory_period:
            final_onsets.append(idx)
            last_onset_time = onset_time

    return np.array(final_onsets)


def detect_onsets_moving_avg(signal_data, fs=1000, window_size=50, refractory_period=0.5):
    moving_avg = np.convolve(np.abs(signal_data), np.ones(window_size)/window_size, mode='valid')
    threshold = np.mean(moving_avg) + 2 * np.std(moving_avg)
    detected_indices = np.where(moving_avg > threshold)[0]

    final_onsets = []
    last_onset_time = -np.inf

    for idx in detected_indices:
        onset_time = idx / fs
        if onset_time - last_onset_time > refractory_period:
            final_onsets.append(idx)
            last_onset_time = onset_time

    return np.array(final_onsets)



def read_serial_data():
    global z
    start_time = time.time()  # Initial time
    baseline_window = deque(maxlen=fs * 2)

    while True:
        while int.from_bytes(esp.read(), "big") != 0xCC:
            pass  # Waits for the sync byte
        
        b1 = int.from_bytes(esp.read(), "big")  # MSB
        b2 = int.from_bytes(esp.read(), "big")  # LSB
        
        adc_val = (b1 << 8) | b2
        voltage = ((adc_val / 4095) * 6.6) - 3.3

        current_time = time.time() - start_time

        # if len(dados) > 0:
        #     mean_voltage = np.mean(dados)
        #     voltage -= mean_voltage

        with lock:
            baseline_window.append(voltage)
            baseline_correction = np.mean(baseline_window) if len(baseline_window) > 0 else 0
            voltage -= baseline_correction
            
            dados.append(voltage)
            timestamp.append(current_time)

            save_dados.append(voltage)
            save_timestamp.append(current_time)

        if len(save_dados) >= fs * 5:
            save_to_csv()


def save_to_csv():
    global save_timestamp, save_dados, onsets_wavelet, onsets_moving_avg
    with lock:
        data_array = np.column_stack((save_timestamp, save_dados))
        save_timestamp = []
        save_dados = []

    with open(nomeArq, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        if csvfile.tell() == 0:  # If the file is empty, write the header
            csvwriter.writerow(['Timestamp', 'Signal', 'Onset Wavelet', 'Onset Moving Average'])
        
        for i, row in enumerate(data_array):
            csvwriter.writerow([row[0], row[1], int(i in onsets_wavelet), int(i in onsets_moving_avg)])
    
    print("Dados salvos em", nomeArq)

class EMGApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EMG Signal")
        self.setGeometry(100, 100, 1000, 600)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        
        self.graph_widget = PlotWidget()
        self.layout.addWidget(self.graph_widget)
        
        self.graph_widget.setLabel('left', 
                                   '<span style="color: white; font-size: 18px">Amplitude (V)</span>')
        self.graph_widget.setLabel('bottom',
                                   '<span style="color: white; font-size: 18px">Time (s)</span>')
        self.graph_widget.setYRange(-3.3, 3.3, padding=0)

        self.graph_widget.addLegend()
        
        self.curve = self.graph_widget.plot([], [], pen=mkPen('g', width=2))
        self.wavelet_lines = []  # List to store the wavelet vertical lines
        self.moving_avg_lines = []  # List to store the moving average vertical lines
        self.wavelet_curve = self.graph_widget.plot([], [], pen=mkPen('b', width=2, style=Qt.PenStyle.DashLine), name="Wavelet")
        self.moving_avg_curve = self.graph_widget.plot([], [], pen=mkPen('r', width=2, style=Qt.PenStyle.DashDotLine), name="Média Móvel")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # 50ms refresh rate
    
    def update_plot(self):
        with lock:
            if len(timestamp) > 0:
                self.curve.setData(timestamp, dados)

                for line in self.wavelet_lines:
                    self.graph_widget.removeItem(line)
                for line in self.moving_avg_lines:
                    self.graph_widget.removeItem(line)
                
                self.wavelet_lines.clear()
                self.moving_avg_lines.clear()

                # Onset detection
                onsets_wavelet_indices = detect_onsets_wavelet(np.array(dados))
                onsets_moving_avg_indices = detect_onsets_moving_avg(np.array(dados))

                global onsets_wavelet, onsets_moving_avg
                onsets_wavelet = [timestamp[i] for i in onsets_wavelet_indices if i < len(timestamp)]
                onsets_moving_avg = [timestamp[i] for i in onsets_moving_avg_indices if i < len(timestamp)]

                # Add vertical lines to the plot
                for onset in onsets_wavelet:
                    line = self.graph_widget.addLine(x=onset, pen=mkPen('r', width=2))
                    self.wavelet_lines.append(line)

                for onset in onsets_moving_avg:
                    line = self.graph_widget.addLine(x=onset, pen=mkPen('b', width=2))
                    self.moving_avg_lines.append(line)

                self.graph_widget.setXRange(max(0, timestamp[-1] - 4), timestamp[-1])  # Janela deslizante de 4s


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EMGApp()
    window.show()

    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
    serial_thread.start()

    sys.exit(app.exec())

esp.close()
print("Conexão com o ESP32 encerrada")