
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
import asyncio
from typing import Optional
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.quic.events import StreamDataReceived
import time
import argparse
import logging

# Set up logging
#create logs folder if it doesnt exist
import os
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filename='logs/quic_server.log')
class HttpServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._http: Optional[H3Connection] = None
        self.c=0
        self.data_queues = {}
        self.accel_queue = None
        self.gyro_queue = None
        self.dual_queue = None
        self.total_messages = 0
        self.accel_count = 0
        self.gyro_count = 0
        self.accel_last_log = time.time()
        self.gyro_last_log = time.time()
        self.accel_start = time.time()
        self.gyro_start = time.time()
        
    async def process_accel_data(self,data):
        """Process accelerometer data, just print it for now"""
        accel = list(map(float, data.split(":")[1].split(",")))
        self.accel_count += 1
        now = time.time()
        if now - self.accel_last_log >= 5:
            self.accel_last_log = now
            total_time = now - self.accel_start
            rate = self.accel_count / total_time
            print(f"Accel rate: {rate:.2f} Hz")
            logging.info(f"[QUIC] Accel rate: {rate:.2f} msgs/sec over {total_time:.2f} seconds")
        print(f"Accel: X={accel[0]:.2f} Y={accel[1]:.2f} Z={accel[2]:.2f} ")
    
    async def process_gyro_data(self,data):
        """Process gyroscope data, just print it for now"""
        gyro = list(map(float, data.split(":")[1].split(",")))
        self.gyro_count += 1
        now = time.time()
        if now - self.gyro_last_log >= 5:
            self.gyro_last_log = now
            rate = self.gyro_count / (now - self.gyro_start)
            logging.info(f"[QUIC] Gyro rate: {rate:.2f} msgs/sec over {now - self.gyro_start:.2f} seconds")
        print(f"Gyro: X={gyro[0]:.2f} Y={gyro[1]:.2f} Z={gyro[2]:.2f}")
    
    async def handle_stream(self,stream_id, sensor_type):
        try:
            queue = self.data_queues.get(stream_id)
            while True:
                if queue.empty():
                    await asyncio.sleep(0)
                    continue
                data = queue.get_nowait()
                
                if sensor_type == 'accel':
                    await self.process_accel_data(data)
                
                elif sensor_type == 'gyro':
                    await self.process_gyro_data(data)
                
                elif sensor_type == 'both':
                    if data.startswith("ACCEL:"):
                        await self.process_accel_data(data)
                    elif data.startswith("GYRO:"):
                        await self.process_gyro_data(data)
        except ConnectionResetError:
            print("Client disconnected")
    
    def quic_event_received(self, event) -> None:
        if isinstance(event, StreamDataReceived):
            # Handle data received on the stream
            stream_id = event.stream_id
            queue = self.data_queues.get(stream_id)
            if queue is None:
                try:
                    data = event.data.decode().strip()
                    
                except UnicodeDecodeError:
                    print(f"Received non-decodable data on stream {stream_id}")
                    return
                if data.startswith("accel"):
                    self.accel_queue = asyncio.Queue(maxsize=1000)
                    self.data_queues[stream_id] = self.accel_queue
                    print(f"Accel stream connected: {stream_id}")
                    self.accel_start = time.time()
                    asyncio.ensure_future(self.handle_stream(event.stream_id, 'accel'))
                    
                elif data.startswith("gyro"):
                    self.gyro_queue = asyncio.Queue(maxsize=1000)
                    self.data_queues[stream_id] = self.gyro_queue
                    print(f"Gyro stream connected: {stream_id}")
                    self.gyro_start = time.time()
                    asyncio.ensure_future(self.handle_stream(event.stream_id,'gyro'))

                elif data.startswith("both"):
                    self.dual_queue = asyncio.Queue(maxsize=1000)
                    self.data_queues[stream_id] = self.dual_queue
                    print(f"Both stream connected: {stream_id}")
                    self.accel_start = time.time()
                    self.gyro_start = time.time()
                    asyncio.ensure_future(self.handle_stream(event.stream_id, 'both'))
            else:
                # Process incoming data
                data = event.data.decode()
                while '\n' in data:
                    line, data = data.split('\n', 1)
                    queue.put_nowait(line)

async def run_server(
    host: str,
    port: int,
    configuration: QuicConfiguration,
) -> None:
    await serve(
        host,
        port,
        configuration=configuration,
        create_protocol=HttpServerProtocol,
    )
    await asyncio.Future()

if __name__ == "__main__":
    configuration = QuicConfiguration(
        is_client=False,
        alpn_protocols=["h3"],
        max_datagram_frame_size=65536
    )
    configuration.load_cert_chain("ssl_cert.pem", "ssl_key.pem")
    argparse = argparse.ArgumentParser(description="QUIC Server for IMU Data")
    argparse.add_argument('--host', type=str, default='local', help='Host to connect to')
    #get args
    args = argparse.parse_args()
    if args.host == 'local':
        host= 'localhost'
    else:
        host = "0.0.0.0"
    try:
        asyncio.run(
                run_server(
                    host=host,
                    port=4433,
                    configuration=configuration,
                )
            )
    except KeyboardInterrupt:
        pass