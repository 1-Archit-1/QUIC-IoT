import serial
import re
class IMUParser:
    """Parser for IMU data"""
    def __init__(self):
        self.pattern = re.compile(r'^(-?\d+\.\d+,){5}-?\d+\.\d+$')
        self.serial_port = '/dev/ttyACM0'
        self.baudrate = 921600

    def match(self, line):
        """Check if the line matches the expected format"""
        return bool(self.pattern.match(line))
    
    def read_serial(self, accel_queue, gyro_queue):
            """Thread function to read from serial port"""
            ser = serial.Serial(self.serial_port, self.baudrate)
            try:
                while True:
                    line = ser.readline().decode().strip()
                    if line and self.pattern.match(line):
                        try:
                            ax, ay, az, gx, gy, gz = map(float, line.split(','))
                            accel_queue.put((ax, ay, az))
                            gyro_queue.put((gx, gy, gz))
                        except ValueError:
                            continue
            finally:
                ser.close()