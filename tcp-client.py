import socket
from queue import Queue
from threading import Thread
import time
import traceback
from imu import IMUParser

class TCPIMUClient:
    def __init__(self, host='localhost', port=5555):
        self.accel_queue = Queue(maxsize=100)
        self.gyro_queue = Queue(maxsize=100)
        self.imu_parser = IMUParser()
        self.running = False
        self.host = host
        self.port = port

    def start(self):
        """Main function to start the client"""
        # Start serial reader thread
        self.running = True
        serial_thread = Thread(target=self.imu_parser.read_serial, args=(self.accel_queue, self.gyro_queue))
        serial_thread.start()

        # TCP connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            print(f"Connected to {self.host}:{self.port}")

            try:
                while self.running:
                    # Send accelerometer data if available
                    if not self.accel_queue.empty():
                        data = self.accel_queue.get()
                        message = f"ACCEL:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n"
                        s.sendall(message.encode())

                    # Send gyroscope data if available
                    if not self.gyro_queue.empty():
                        data = self.gyro_queue.get()
                        message = f"GYRO:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n"
                        s.sendall(message.encode())

                    # Small delay to prevent CPU overload
                    time.sleep(0)

            except Exception as e:
                print(f"Connection closed {traceback.format_exc()}")
            finally:
                self.running = False
                serial_thread.join()

if __name__ == "__main__":
    client = TCPIMUClient()
    client.start()