import serial
import re
import asyncio
from queue import Queue
from threading import Thread
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect
from quic_priority import PriorityManager
import traceback
class IMUClient:
    def __init__(self):
        self.queues = {}
        self.serial_port = '/dev/ttyACM0'
        self.baudrate = 921600
        self.running = False
        self.parser = re.compile(r'^(-?\d+\.\d+,){5}-?\d+\.\d+$')
        self.priority_mgr = PriorityManager()
        self.queues = {}
        self.stream_ids = {}
        self.stream_details = {}
        self.connection = None

    async def create_tagged_stream(self, tag, weight):
        """Create a new stream and return its ID."""
        stream_id = self.connection._quic.get_next_available_stream_id(is_unidirectional=True)
        reader,writer = self.connection._create_stream(stream_id)
        self.stream_ids[tag] = stream_id
        self.stream_details[stream_id] = {'weight': weight, 'tag': tag, 'writer': writer}
        bytes = tag.encode()
        writer.write(bytes)
        await writer.drain()
        self.priority_mgr.add_stream(stream_id=stream_id, weight=weight) 
        self.queues[stream_id] = asyncio.Queue(maxsize=100)


    async def process_data(self):
        """Process data from the queues."""
        while self.running:
            ready_streams = []
            for sid, queue in self.queues.items():
                if not queue.empty():
                    ready_streams.append(sid)
            if ready_streams:
                if len(ready_streams) == 1:
                    selected_stream = ready_streams[0]
                else:
                    selected_stream = self.priority_mgr.get_next_stream(ready_streams)
                stream_details = self.stream_details[selected_stream]
                writer = stream_details['writer']
                tag = stream_details['tag']
                queue = self.queues[selected_stream]
                data = await queue.get()
                msg = f"{tag}:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode()
                print(f"Sending data on stream {selected_stream}: {msg}")
                writer.write(msg)
                await writer.drain()
                self.priority_mgr.update_after_send(selected_stream)
                await asyncio.sleep(0)
        # except Exception as e:
        #     print(f"Error in process_data: {traceback.format_exc()}")
        # finally:
        #     for stream_id in self.stream_ids.values():
        #         if stream_id in self.queues:
        #             del self.queues[stream_id]
        #         if stream_id in self.writers:
        #             del self.writers[stream_id]
        #     print("All streams closed and cleaned up.")
        #     self.running = False
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
            
            """Create Streams"""
            await self.create_tagged_stream(tag = 'accel',weight=256) 
            await self.create_tagged_stream(tag = 'gyro',weight=30)

            # Start serial reader thread
            self.running = True
            serial_thread = Thread(target=self.read_serial)
            serial_thread.start()
            self.acc = 0
            self.gy = 0

            while self.running:
                ready_streams = []
                for sid, queue in self.queues.items():
                    if not queue.empty():
                        ready_streams.append(sid)
                if ready_streams:
                    if len(ready_streams) == 1:
                        selected_stream = ready_streams[0]
                    else:
                        selected_stream = self.priority_mgr.get_next_stream(ready_streams)
                    stream_details = self.stream_details[selected_stream]
                    writer = stream_details['writer']
                    tag = stream_details['tag']
                    queue = self.queues[selected_stream]
                    data = await queue.get()
                    msg = f"{tag}:{data[0]:.3f},{data[1]:.3f},{data[2]:.3f}\n".encode()
                    print(f"Sending data on stream {selected_stream}: {msg}")
                    writer.write(msg)
                    await writer.drain()
                    self.priority_mgr.update_after_send(selected_stream)
                    await asyncio.sleep(0)


    def read_serial(self):
        ser = serial.Serial(self.serial_port, self.baudrate, timeout=0.1)
        try:
            while self.running:
                line = ser.readline().decode().strip()
                if line and self.parser.match(line):
                    try:
                        print(line)
                        ax, ay, az, gx, gy, gz = map(float, line.split(','))
                        acc_sid = self.stream_ids['accel']
                        gyro_sid = self.stream_ids['gyro']
                        self.queues[acc_sid].put_nowait((ax, ay, az))
                        self.queues[gyro_sid].put_nowait((gx, gy, gz))
                    except ValueError:
                        continue
        finally:
            ser.close()

if __name__ == "__main__":
    client = IMUClient()
    asyncio.run(client.start())