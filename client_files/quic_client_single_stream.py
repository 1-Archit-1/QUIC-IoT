import asyncio
from queue import Queue
from threading import Thread
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect
from helpers import IMUParser
import argparse

SERVER = "172.190.228.31"

class IMUClientSingleStream:
    def __init__(self):
        self.gyro_queue = Queue(maxsize=1000)
        self.accel_queue = Queue(maxsize=1000)
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
            reader, writer = connection._create_stream(a_sid)
            writer.write(b'both')

            self.running = True
            serial_thread = Thread(target=self.imu_parser.read_serial, args=(self.accel_queue,self.gyro_queue,))
            serial_thread.start()

            try:
                while self.running:
                    if not self.accel_queue.empty():
                        data = self.accel_queue.get()
                        writer.write(f"ACCEL:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode())
                        await writer.drain()
                    if not self.gyro_queue.empty():
                        data = self.gyro_queue.get()
                        writer.write(f"GYRO:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode())
                        await writer.drain()
                    await asyncio.sleep(0)

            finally:
                self.running = False
                serial_thread.join()

if __name__ == "__main__":
    client = IMUClientSingleStream()
    #add cli args
    argparse = argparse.ArgumentParser(description="QUIC Client for IMU Data")
    argparse.add_argument('--host', type=str, default='local', help='Host to connect to')
    #get args 
    args = argparse.parse_args()
    if args.host == 'local':
        host= 'localhost'
    else:
        host = SERVER
    asyncio.run(client.start(host))