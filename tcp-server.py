import socket
import threading
import queue
from datetime import datetime
from collections import deque
import asyncio
import traceback

class TCPIMUServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_count = 0
        self.message_queue =  asyncio.Queue()
        self.buffer_size = 4096 
        self.client_buffers = {}

    async def process_accel_data(self,data):
        """Process accelerometer data."""
        accel = list(map(float, data.split(":")[1].split(",")))
        print(f"Accel: X={accel[0]:.2f} Y={accel[1]:.2f} Z={accel[2]:.2f} ")
    
    async def process_gyro_data(self,data):
        """Process gyroscope data."""
        gyro = list(map(float, data.split(":")[1].split(",")))
        print(f"Gyro: X={gyro[0]:.2f} Y={gyro[1]:.2f} Z={gyro[2]:.2f}")

    async def process_messages(self):
        """Separate thread for processing messages from the queue"""
        while True:
            try:
                if self.message_queue.empty():
                    await asyncio.sleep(0)
                    continue
                message = self.message_queue.get_nowait()
                if message.startswith("ACCEL:"):                    
                    await self.process_accel_data(message)
                elif message.startswith("GYRO:"):
                    await self.process_gyro_data(message)
                self.message_queue.task_done()
            except queue.Empty:
                continue

    async def handle_client(self, reader, writer):
        """Handle individual client connection with complete message reading"""
        
        addr = writer.get_extra_info('peername')
        print(f"New connection from {addr}")
        self.client_count += 1
        buffer = b''
        
        try:
            while True:
                # Receive data
                data = await reader.read(4096)
                if not data:
                    break
                
                buffer += data
                while b'\n' in buffer:
                    message, buffer = buffer.split(b'\n', 1)
                    await self.message_queue.put(message.decode().strip())
                
        except Exception as e:
            print(f"Error handling client {traceback.format_exc()}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.client_count -= 1
            print(f"Client {addr} disconnected")

    async def start(self):
        """Start the TCP server with processing thread"""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        asyncio.create_task(self.process_messages())
        
        print(f"Server listening on {self.host}:{self.port}")
        async with self.server:
            await self.server.serve_forever()


if __name__ == "__main__":
    server = TCPIMUServer()
    asyncio.run(server.start())