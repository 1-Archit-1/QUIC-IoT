
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
import asyncio
from typing import Optional
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.quic.events import StreamDataReceived
from imu import IMUParser

class HttpServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._http: Optional[H3Connection] = None
        self.c=0
        self.data_queues = {}
        self.imu_parser = IMUParser()
        self.accel_queue = asyncio.Queue(maxsize=100)
        self.gyro_queue = asyncio.Queue(maxsize=100)
    
    async def process_accel_data(self,data):
        """Process accelerometer data, just print it for now"""
        accel = list(map(float, data.split(":")[1].split(",")))
        print(f"Accel: X={accel[0]:.2f} Y={accel[1]:.2f} Z={accel[2]:.2f} ")
    
    async def process_gyro_data(self,data):
        """Process gyroscope data, just print it for now"""
        gyro = list(map(float, data.split(":")[1].split(",")))
        print(f"Gyro: X={gyro[0]:.2f} Y={gyro[1]:.2f} Z={gyro[2]:.2f}")
    
    async def handle_stream(self,stream_id, sensor_type):
        try:
            queue = self.data_queues.get(stream_id)
            while True:
                data = await queue.get()
                if not data:
                    asyncio.sleep(0)
                    continue
                if sensor_type == 'accel':
                    await self.process_accel_data(data)
                elif sensor_type == 'gyro':
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
                    self.data_queues[stream_id] = self.accel_queue
                    print(f"Accel stream connected: {stream_id}")
                    asyncio.ensure_future(self.handle_stream(event.stream_id, 'accel'))
                elif data.startswith("gyro"):
                    self.data_queues[stream_id] = self.gyro_queue
                    print(f"Gyro stream connected: {stream_id}")
                    asyncio.ensure_future(self.handle_stream(event.stream_id,'gyro'))
            else:
                # Process incoming data
                queue.put_nowait(event.data.decode().strip())

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
    
    try:
        asyncio.run(
                run_server(
                    host='localhost',
                    port=4433,
                    configuration=configuration,
                )
            )
    except KeyboardInterrupt:
        pass