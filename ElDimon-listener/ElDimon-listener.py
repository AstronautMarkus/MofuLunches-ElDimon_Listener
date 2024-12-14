import os
import serial
import time
import sys
import json
from PyQt5 import QtWidgets, QtCore, QtGui
from threading import Thread
from PyQt5.QtGui import QIcon

def detectar_arduino():
    """
    Detect connected Arduino devices.
    """
    dispositivos = os.listdir('/dev')
    arduino_ports = [d for d in dispositivos if 'ttyUSB' in d or 'ttyACM' in d]
    return arduino_ports

def listen_serial(app, baudrate=9600):
    status = {"code": 10, "message": "Trying to connect"}

    def print_json(data):
        """
        Ensure the data is valid JSON before printing.
        """
        try:
            print(json.dumps(data))
            sys.stdout.flush()
        except (TypeError, ValueError) as e:
            print(json.dumps({"code": 60, "message": f"Error formatting JSON: {e}"}))
            sys.stdout.flush()

    def convert_to_integer(data_str):
        """
        Convert a string of hexadecimal values into a single integer.
        """
        try:
            hex_str = ''.join(data_str.split())
            return int(hex_str, 16)
        except ValueError as e:
            print_json({"code": 60, "message": f"Error converting data to integer: {e}"})
            return None

    while True:
        try:
            arduino_ports = detectar_arduino()
            if not arduino_ports:
                print_json({"code": 10, "message": "No Arduino device detected. Retrying in 5 seconds..."})
                app.update_status("No Arduino device detected. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            port = f"/dev/{arduino_ports[0]}"
            print_json({"code": 10, "message": f"Trying to connect with {port}"})
            app.update_status(f"Trying to connect with {port}")

            ser = serial.Serial(port, baudrate, timeout=1)
            status = {"code": 20, "message": f"Successfully connected on {port}"}
            print_json(status)
            app.update_status(f"Successfully connected on {port}")

            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    int_value = convert_to_integer(line)
                    if int_value is not None:
                        data = {"code": 30, "data": int_value}
                        print_json(data)
                        app.update_data(int_value)

        except serial.SerialException as e:
            error_message = f"Connection error on {port}. Retrying: {e}"
            print_json({"code": 10, "message": error_message})
            app.update_status(error_message)

            print_json({"code": 10, "message": "Retrying connection in 5 seconds..."})
            app.update_status("Retrying connection in 5 seconds...")
            time.sleep(5)

        except UnicodeDecodeError as e:
            print_json({"code": 40, "message": f"Warning: Decoding error - {e}"})
            app.update_status(f"Warning: Decoding error - {e}")

        except Exception as e:
            print_json({"code": 60, "message": f"Unexpected error: {e}"})
            app.update_status(f"Unexpected error: {e}")

        finally:
            if 'ser' in locals() and ser.is_open:
                ser.close()
                print_json({"code": 10, "message": "Port closed. Retrying..."})
                app.update_status("Port closed. Retrying...")

class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("MofuLunches - ElDimon Listener")
        self.setFixedSize(800, 600)
        self.setWindowIcon(QIcon('icon.png'))  # Set window icon

        layout = QtWidgets.QVBoxLayout()

        # Title and instructions
        title_layout = QtWidgets.QHBoxLayout()
        title_layout.setAlignment(QtCore.Qt.AlignCenter)  # Center the title layout

        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(QtGui.QPixmap('icon.png').scaled(60, 60, QtCore.Qt.KeepAspectRatio))  # Adjust icon size
        title_layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel("ElDimon Listener")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #333;")  # Adjust title size
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_layout.addWidget(title_label)

        layout.addLayout(title_layout)

        instructions_label = QtWidgets.QLabel(
            "1. Connect the ElDimon device.\n"
            "2. Place an RFID card on the reader.\n"
            "3. The code will be displayed automatically."
        )
        instructions_label.setStyleSheet("font-size: 16px; color: #555;")
        instructions_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(instructions_label)

        # Field to display the scanned code
        self.label = QtWidgets.QLabel("Scanned Code:")
        self.label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        self.label.setAlignment(QtCore.Qt.AlignCenter)  # Center text
        layout.addWidget(self.label)

        self.code_var = QtWidgets.QLineEdit()
        self.code_var.setReadOnly(True)
        self.code_var.setStyleSheet("font-size: 16px; padding: 10px; background-color: #f5f5f5; color: #333;")
        self.code_var.setFixedWidth(400)  # Reduce width
        self.code_var.setAlignment(QtCore.Qt.AlignCenter)  # Center text
        layout.addWidget(self.code_var, alignment=QtCore.Qt.AlignCenter)

        # Button to copy the code
        self.copy_button = QtWidgets.QPushButton("Copy Code")
        self.copy_button.setStyleSheet("font-size: 16px; padding: 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;")
        self.copy_button.setFixedWidth(200)  # Reduce width
        self.copy_button.clicked.connect(self.copy_code)
        layout.addWidget(self.copy_button, alignment=QtCore.Qt.AlignCenter)

        # Button to clear the code
        self.clear_button = QtWidgets.QPushButton("Clear Code")
        self.clear_button.setStyleSheet("font-size: 16px; padding: 10px; background-color: #F39C12; color: white; border: none; border-radius: 5px;")
        self.clear_button.setFixedWidth(200)  # Reduce width
        self.clear_button.clicked.connect(self.clear_code)
        layout.addWidget(self.clear_button, alignment=QtCore.Qt.AlignCenter)

        # Label for copy confirmation message
        self.copy_message_label = QtWidgets.QLabel(" ")
        self.copy_message_label.setStyleSheet("font-size: 16px; color: green;")
        self.copy_message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.copy_message_label.setVisible(False)
        self.copy_message_label.setFixedHeight(20)  # Reserve space for the label
        layout.addWidget(self.copy_message_label)

        # Connection status
        self.status_label = QtWidgets.QLabel("Status: Waiting for device...")
        self.status_label.setStyleSheet("font-size: 16px; color: #555;")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)  # Center text
        layout.addWidget(self.status_label)

        # Exit button
        self.exit_button = QtWidgets.QPushButton("Exit")
        self.exit_button.setStyleSheet("font-size: 16px; padding: 10px; background-color: #E74C3C; color: white; border: none; border-radius: 5px;")
        self.exit_button.setFixedWidth(200)  # Reduce width
        self.exit_button.clicked.connect(self.close)
        layout.addWidget(self.exit_button, alignment=QtCore.Qt.AlignCenter)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #fdfdfd;")
        self.show()

    def update_data(self, data):
        self.code_var.setText(str(data))

    def copy_code(self):
        if not self.code_var.text().strip():
            self.show_copy_message("No code to copy", "#8B0000")  # Darker red
            return

        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.code_var.text())
        self.show_copy_message("Code copied to clipboard", "green")

    def clear_code(self):
        self.code_var.clear()
        self.show_copy_message("Code cleared", "orange")

    def show_copy_message(self, message, color):
        self.copy_message_label.setText(message)
        self.copy_message_label.setStyleSheet(f"font-size: 16px; color: {color};")
        self.copy_message_label.setVisible(True)
        self.fade_out_copy_message()

    def fade_out_copy_message(self):
        self.animation = QtCore.QPropertyAnimation(self.copy_message_label, b"opacity")
        self.animation.setDuration(2000)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(lambda: self.copy_message_label.setText(" "))
        self.animation.start()

    def update_status(self, status):
        self.status_label.setText(f"Status: {status}")

    def closeEvent(self, event):
        sys.exit()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_app = App()

    # Run the listener in a separate thread
    serial_thread = Thread(target=listen_serial, args=(main_app,))
    serial_thread.daemon = True
    serial_thread.start()

    sys.exit(app.exec_())
