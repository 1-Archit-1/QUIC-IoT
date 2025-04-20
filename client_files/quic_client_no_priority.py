import asyncio
from queue import Queue
from threading import Thread
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect
from helpers import IMUParser
import argparse

SERVER_URL = '172.190.228.31'

class IMUClientNoPriority:
    """QUIC client for sending IMU data to a server with no priority management."""
    def __init__(self):
        self.accel_queue = Queue(maxsize=1000)
        self.gyro_queue = Queue(maxsize=1000)
        self.imu_parser = IMUParser()
        self.running = False
        
    async def start(self, host):
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["h3"],
            max_datagram_frame_size=65536,
            verify_mode=False
        )

        async with connect(host, 4433, configuration=configuration) as connection:
            # Create separate streams
            a_sid = connection._quic.get_next_available_stream_id(is_unidirectional=True)
            accel_reader, accel_writer = connection._create_stream(a_sid)
            accel_writer.write(b"accel")
            await accel_writer.drain()
            g_sid = connection._quic.get_next_available_stream_id(is_unidirectional=True)
            gyro_reader, gyro_writer = connection._create_stream(g_sid)
            gyro_writer.write(b"gyro")
            await gyro_writer.drain()
            self.running = True
            serial_thread = Thread(target=self.imu_parser.read_serial, args=(self.accel_queue, self.gyro_queue))
            serial_thread.start()

            try:
                while self.running:
                    # Send accelerometer data
                    if not self.accel_queue.empty():
                        data = self.accel_queue.get()
                        accel_writer.write(f"ACCEL:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode())
                        await accel_writer.drain()

                    # Send gyroscope data
                    if not self.gyro_queue.empty():
                        data = self.gyro_queue.get()
                        gyro_writer.write(f"GYRO:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode())
                        await gyro_writer.drain()

                    await asyncio.sleep(0)

            finally:
                self.running = False
                serial_thread.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QUIC IMU Client")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    args = parser.parse_args()
    if args.host == "local":
        host = "localhost"
    else:
        host = SERVER_URL 
    client = IMUClientNoPriority()
    asyncio.run(client.start())