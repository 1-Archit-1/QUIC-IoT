import serial
import re
import asyncio
from queue import Queue
from threading import Thread
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect

class IMUClient:
    def __init__(self):
        self.accel_queue = Queue(maxsize=100)
        self.gyro_queue = Queue(maxsize=100)
        self.serial_port = '/dev/ttyACM0'
        self.baudrate = 921600
        self.running = False
        self.parser = re.compile(r'^(-?\d+\.\d+,){5}-?\d+\.\d+$')
        
    async def start(self):
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["h3"],
            max_datagram_frame_size=65536,
            verify_mode=False
        )

        async with connect("localhost", 4433, configuration=configuration) as connection:
            # Create separate streams
            a_sid = connection._quic.get_next_available_stream_id(is_unidirectional=True)
            accel_reader, accel_writer = connection._create_stream(a_sid)
            accel_writer.write(b"ACCE")
            print(a_sid)
            g_sid = connection._quic.get_next_available_stream_id(is_unidirectional=True)
            print(g_sid)
            gyro_reader, gyro_writer = connection._create_stream(g_sid)
            gyro_writer.write(b"GYRO")
            self.running = True
            serial_thread = Thread(target=self.read_serial)
            serial_thread.start()

            try:
                while self.running:
                    # Send accelerometer data
                    if not self.accel_queue.empty():
                        data = self.accel_queue.get()
                        accel_writer.write(f"ACCEL:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}".encode())
                        await accel_writer.drain()

                    # Send gyroscope data
                    if not self.gyro_queue.empty():
                        data = self.gyro_queue.get()
                        gyro_writer.write(f"GYRO:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}".encode())
                        await gyro_writer.drain()

                    await asyncio.sleep(0)  # 1ms delay

            finally:
                self.running = False
                serial_thread.join()

    def read_serial(self):
        ser = serial.Serial(self.serial_port, self.baudrate, timeout=0.1)
        try:
            while self.running:
                line = ser.readline().decode().strip()
                #print(line)
                if line and self.parser.match(line):
                    ax, ay, az, gx, gy, gz = map(float, line.split(','))
                    self.accel_queue.put((ax, ay, az))
                    self.gyro_queue.put((gx, gy, gz))
        finally:
            ser.close()

if __name__ == "__main__":
    client = IMUClient()
    asyncio.run(client.start())