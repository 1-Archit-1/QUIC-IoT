import asyncio
from queue import Queue
from threading import Thread
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect
from quic_priority import PriorityManager
from imu import IMUParser
class IMUClient:
    def __init__(self):
        self.accel_queue = Queue(maxsize=100)
        self.gyro_queue = Queue(maxsize=100)
        self.running = False
        self.imu_parser = IMUParser()
        self.priority_mgr = PriorityManager()
        self.stream_ids = {}

    async def create_tagged_stream(self, tag, weight):
        """Create a new stream and return its ID."""
        stream_id = self.connection._quic.get_next_available_stream_id(is_unidirectional=True)
        reader,writer = self.connection._create_stream(stream_id)
        self.stream_ids[tag] = stream_id
        bytes = tag.encode()
        writer.write(bytes)
        await writer.drain()
        self.priority_mgr.add_stream(stream_id=stream_id, weight=weight)
        return writer
    
    async def start(self):
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["h3"],
            max_datagram_frame_size=65536,
            verify_mode=False
        )

        async with connect("localhost", 4433, configuration=configuration) as connection:
            # Create and register streams
            self.connection = connection
            accel_writer = await self.create_tagged_stream("accel", weight=256)  # Higher priority
            gyro_writer = await self.create_tagged_stream("gyro", weight=128)  # Lower priority
            # Start serial reader thread
            self.running = True
            serial_thread = Thread(target=self.imu_parser.read_serial, args=(self.accel_queue, self.gyro_queue))
            serial_thread.start()

            try:
                while self.running:
                    # Check which streams have data
                    ready_streams = []
                    streams_writers = {}
                    
                    if not self.accel_queue.empty():
                        ready_streams.append(self.stream_ids['accel'])
                        streams_writers[self.stream_ids['accel']] = (accel_writer, self.accel_queue)
                        
                    if not self.gyro_queue.empty():
                        ready_streams.append(self.stream_ids['gyro'])
                        streams_writers[self.stream_ids['gyro']] = (gyro_writer, self.gyro_queue)

                    # Let priority manager decide which to send next
                    if ready_streams:
                        selected_stream = self.priority_mgr.get_next_stream(ready_streams)
                        if selected_stream:
                            writer, queue = streams_writers[selected_stream]
                            data = queue.get()
                            
                            if selected_stream == self.stream_ids['accel']:
                                msg = f"ACCEL:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode()
                            else:
                                msg = f"GYRO:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode()
                            
                            writer.write(msg)
                            await writer.drain()
                            self.priority_mgr.update_after_send(selected_stream)

                    await asyncio.sleep(0)  # Prevent busy waiting

            finally:
                self.running = False
                serial_thread.join()

if __name__ == "__main__":
    client = IMUClient()
    asyncio.run(client.start())