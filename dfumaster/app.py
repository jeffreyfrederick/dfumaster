from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox, QListWidget, QStatusBar, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
import os
import re
import subprocess

# Paths
project_root = os.path.dirname(os.path.abspath(__file__))
ipsw_dir = os.path.join(project_root, 'ipsw')
ipsw_files = [f for f in os.listdir(ipsw_dir) if f.endswith('.ipsw')]
ipsw_path = os.path.join(ipsw_dir, ipsw_files[0]) if len(ipsw_files) == 1 else None


class RestoreWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal()

    def run(self):
        try:
            self.progress.emit(25)
            self.status.emit("Detecting device...")

            os.chdir('/Applications/Apple Configurator.app/Contents/MacOS/')
            result = subprocess.run(['cfgutil', 'list'], stdout=subprocess.PIPE, text=True)
            matches = re.findall(r'ECID:\s*(0x[0-9A-Fa-f]+)', result.stdout)

            if matches:
                for ecid in matches:
                    self.status.emit(f"Restoring {ecid}...")
                    restore_cmd = f'cfgutil -e {ecid} restore -I "{ipsw_path}"'
                    subprocess.run(restore_cmd, shell=True)
                    self.progress.emit(100)
                    self.status.emit("Restore complete.")
            else:
                self.status.emit("No device found in DFU mode.")
        except Exception as e:
            self.status.emit(f"Restore error: {e}")
        finally:
            self.finished.emit()


class DFUWorker(QThread):
    status = Signal(str)
    finished = Signal()

    def run(self):
        try:
            self.status.emit("Entering DFU mode...")
            subprocess.run(['sudo', 'macvdmtool', 'dfu'])
            self.status.emit("DFU mode triggered.")
        except Exception as e:
            self.status.emit(f"DFU error: {e}")
        finally:
            self.finished.emit()


class RebootWorker(QThread):
    status = Signal(str)
    finished = Signal()

    def run(self):
        try:
            self.status.emit("Rebooting device...")
            subprocess.run(['sudo', 'macvdmtool', 'reboot'])
            self.status.emit("Reboot command sent.")
        except Exception as e:
            self.status.emit(f"Reboot error: {e}")
        finally:
            self.finished.emit()


class DeviceDetectionWorker(QThread):
    devices_detected = Signal(list)
    status = Signal(str)

    def run(self):
        try:
            os.chdir('/Applications/Apple Configurator.app/Contents/MacOS/')
            result = subprocess.run(['cfgutil', 'list'], stdout=subprocess.PIPE, text=True)
            matches = re.findall(r'ECID:\s*(0x[0-9A-Fa-f]+)', result.stdout)
            self.devices_detected.emit(matches)
        except Exception as e:
            self.status.emit(f"Detection error: {e}")


class DFURestoreApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFU Master")
        self.setMinimumSize(500, 300)

        self.previous_ecids = set()
        self.auto_dfu_triggered_ecids = set()

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.device_count_label = QLabel("No devices detected.")
        self.device_list = QListWidget()

        self.auto_dfu_checkbox = QCheckBox("Auto DFU Mode")
        self.auto_dfu_checkbox.setChecked(False)

        self.dfu_btn = QPushButton("Enter DFU Mode")
        self.dfu_btn.clicked.connect(self.enter_dfu)

        self.reboot_btn = QPushButton("Restart Device")
        self.reboot_btn.clicked.connect(self.reboot_device)

        self.restore_btn = QPushButton("Start Restore")
        self.restore_btn.clicked.connect(self.on_restore)

        if not ipsw_path:
            self.restore_btn.setEnabled(False)
            QMessageBox.critical(
                self, "IPSW Error",
                "There must be exactly one .ipsw file in the 'ipsw' folder.\n\n"
                f"Found: {len(ipsw_files)}"
            )

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.device_count_label)
        layout.addWidget(self.device_list)
        layout.addWidget(self.auto_dfu_checkbox)
        layout.addWidget(self.dfu_btn)
        layout.addWidget(self.restore_btn)
        layout.addWidget(self.reboot_btn)

        self.setCentralWidget(central_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.set_status("Ready.")

        self.device_timer = QTimer()
        self.device_timer.timeout.connect(self.start_device_detection)
        self.device_timer.start(2000)

    def set_status(self, msg):
        self.status_bar.showMessage(msg)

    def update_progress(self, percent):
        self.progress_bar.setValue(percent)

    def start_device_detection(self):
        self.detection_thread = DeviceDetectionWorker()
        self.detection_thread.devices_detected.connect(self.handle_device_results)
        self.detection_thread.status.connect(self.set_status)
        self.detection_thread.start()

    def handle_device_results(self, ecids):
        current_ecids = set(ecids)

        if current_ecids != self.previous_ecids:
            self.device_list.clear()
            for ecid in current_ecids:
                self.device_list.addItem(ecid)

            new_devices = current_ecids - self.previous_ecids
            if self.auto_dfu_checkbox.isChecked():
                for ecid in new_devices:
                    if ecid not in self.auto_dfu_triggered_ecids:
                        self.auto_dfu_triggered_ecids.add(ecid)
                        self.enter_dfu()

            self.previous_ecids = current_ecids

        label = f"{len(current_ecids)} device(s) detected." if current_ecids else "No devices detected."
        self.device_count_label.setText(label)

    def set_buttons_enabled(self, enabled):
        self.restore_btn.setEnabled(enabled)
        self.dfu_btn.setEnabled(enabled)
        self.reboot_btn.setEnabled(enabled)

    def enter_dfu(self):
        self.set_buttons_enabled(False)
        self.dfu_thread = DFUWorker()
        self.dfu_thread.status.connect(self.set_status)
        self.dfu_thread.finished.connect(lambda: self.set_buttons_enabled(True))
        self.dfu_thread.start()

    def on_restore(self):
        self.set_buttons_enabled(False)
        self.update_progress(0)

        self.restore_thread = RestoreWorker()
        self.restore_thread.status.connect(self.set_status)
        self.restore_thread.progress.connect(self.update_progress)
        self.restore_thread.finished.connect(lambda: self.set_buttons_enabled(True))
        self.restore_thread.start()

    def reboot_device(self):
        self.set_buttons_enabled(False)

        self.reboot_thread = RebootWorker()
        self.reboot_thread.status.connect(self.set_status)
        self.reboot_thread.finished.connect(lambda: self.set_buttons_enabled(True))
        self.reboot_thread.start()


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("DFU Master")
    window = DFURestoreApp()
    window.show()
    app.exec()
