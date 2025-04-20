from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
import asyncio
from typing import Optional
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.quic.events import StreamDataReceived
import time
import argparse
import logging
import signal

# Set up logging
import os
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', 
                    filename='logs/quic_server.log')

class HttpServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._http: Optional[H3Connection] = None
        self.data_queues = {}
        self.accel_queue = None
        self.gyro_queue = None
        self.dual_queue = None
        self.accel_count = 0
        self.gyro_count = 0
        self.accel_last_log = time.time()
        self.gyro_last_log = time.time()
        self._start_time = time.time()
        self._shutdown = False
        self._processing_task = None
    def process_rate_logging(self, sensor_type):
        """Log the rate of incoming data"""
        now = time.time()
        if sensor_type == 'accel' or 'both':
            rate = self.accel_count / (now - self._start_time)
            logging.info(f"Accel rate: {rate:.2f} msgs/sec over {now - self._start_time:.2f} seconds")
        elif sensor_type == 'gyro' or 'both':
            rate = self.gyro_count / (now - self._start_time)
            logging.info(f"Gyro rate: {rate:.2f} msgs/sec over {now - self._start_time:.2f} seconds")
    async def process_accel_data(self, data):
        """Process accelerometer data"""
        try:
            accel = list(map(float, data.split(":")[1].split(",")))
            self.accel_count += 1
            now = time.time()
            if now - self.accel_last_log >= 5:
                self.accel_last_log = now
                self.process_rate_logging('accel')
            print(f"Accel: X={accel[0]:.2f} Y={accel[1]:.2f} Z={accel[2]:.2f}")
        except Exception as e:
            logging.error(f"Error processing accel data: {e}")

    async def process_gyro_data(self, data):
        """Process gyroscope data"""
        try:
            gyro = list(map(float, data.split(":")[1].split(",")))
            self.gyro_count += 1
            now = time.time()
            if now - self.gyro_last_log >= 5:
                self.gyro_last_log = now
                self.process_rate_logging('gyro')
            print(f"Gyro: X={gyro[0]:.2f} Y={gyro[1]:.2f} Z={gyro[2]:.2f}")
        except Exception as e:
            logging.error(f"Error processing gyro data: {e}")

    async def handle_stream(self, stream_id, sensor_type):
        """Handle data stream processing"""
        try:
            logging.info(f"Starting to handle {sensor_type} stream")
            queue = self.data_queues.get(stream_id)
            if queue is None:
                return

            while not self._shutdown or not queue.empty():
                try:
                    data = await queue.get()
                    if data == '0':  # Sentinel value for shutdown
                        print('rate logging ?')
                        self.process_rate_logging(sensor_type)
                        break

                    if sensor_type == 'accel':
                        await self.process_accel_data(data)
                    elif sensor_type == 'gyro':
                        await self.process_gyro_data(data)
                    elif sensor_type == 'both':
                        if data.startswith("ACCEL:"):
                            await self.process_accel_data(data)
                        elif data.startswith("GYRO:"):
                            await self.process_gyro_data(data)

                    queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logging.error(f"Error in stream handler: {e}")
                    break

            logging.info(f"Finished processing {sensor_type} stream")
        except Exception as e:
            logging.error(f"Stream handler error: {e}")

    def quic_event_received(self, event) -> None:
        if self._shutdown:
            return

        if isinstance(event, StreamDataReceived):
            stream_id = event.stream_id
            queue = self.data_queues.get(stream_id)
            
            if queue is None:
                try:
                    data = event.data.decode().strip()
                except UnicodeDecodeError:
                    logging.error("Received non-decodable data")
                    return

                if data.startswith("accel"):
                    self.accel_queue = asyncio.Queue(maxsize=1000)
                    self.data_queues[stream_id] = self.accel_queue
                    logging.info("Accel stream connected")
                    self._processing_task = asyncio.create_task(
                        self.handle_stream(stream_id, 'accel')
                    )
                    
                elif data.startswith("gyro"):
                    self.gyro_queue = asyncio.Queue(maxsize=1000)
                    self.data_queues[stream_id] = self.gyro_queue
                    logging.info("Gyro stream connected")
                    self._processing_task = asyncio.create_task(
                        self.handle_stream(stream_id, 'gyro')
                    )

                elif data.startswith("both"):
                    self.dual_queue = asyncio.Queue(maxsize=1000)
                    self.data_queues[stream_id] = self.dual_queue
                    logging.info("Dual stream connected")
                    self._processing_task = asyncio.create_task(
                        self.handle_stream(stream_id, 'both')
                    )
            else:
                try:
                    data = event.data.decode()
                    while '\n' in data:
                        line, data = data.split('\n', 1)
                        queue.put_nowait(line)
                except Exception as e:
                    logging.error(f"Error processing incoming data: {e}")

    async def shutdown(self):
        """Gracefully shutdown the protocol"""
        if self._shutdown:
            return
            
        self._shutdown = True
        logging.info("Starting protocol shutdown")
        
        # Signal queues to stop
        for queue in self.data_queues.values():
            try:
                await queue.put('0')  # Sentinel value to stop processing
            except Exception as e:
                logging.error(f"Error putting sentinel to queue: {e}")
            
        # Wait for processing task to complete
        if self._processing_task:
            try:
                await asyncio.wait_for(self._processing_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logging.error(f"Error during shutdown: {e}")
                
        logging.info("Protocol shutdown complete")

async def run_server(
    host: str,
    port: int,
    configuration: QuicConfiguration,
    shutdown_event: asyncio.Event
) -> None:
    server = None
    protocol = None
    
    def protocol_factory(*args, **kwargs):
        nonlocal protocol
        protocol = HttpServerProtocol(*args, **kwargs)
        return protocol

    try:
        server = await serve(
            host,
            port,
            configuration=configuration,
            create_protocol=protocol_factory,
        )
        
        logging.info(f"Server started on {host}:{port}")
        await shutdown_event.wait()
        logging.info("Server shutdown initiated")
        
    except asyncio.CancelledError:
        logging.info("Server received cancellation")
    finally:
        if server:
            if protocol:
                await protocol.shutdown()
            server.close()
            await asyncio.sleep(0.1)
            logging.info("Server closed")

def handle_sigint(shutdown_event: asyncio.Event):
    """Signal handler for SIGINT"""
    logging.info("Received SIGINT, initiating shutdown")
    shutdown_event.set()

async def main():
    configuration = QuicConfiguration(
        is_client=False,
        alpn_protocols=["h3"],
        max_datagram_frame_size=65536
    )
    configuration.load_cert_chain("ssl_cert.pem", "ssl_key.pem")
    
    parser = argparse.ArgumentParser(description="QUIC Server for IMU Data")
    parser.add_argument('--host', type=str, default='local', help='Host to connect to')
    args = parser.parse_args()
    
    host = 'localhost' if args.host == 'local' else "0.0.0.0"
    
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    
    # Set up signal handler
    try:
        loop.add_signal_handler(
            signal.SIGINT, 
            lambda: handle_sigint(shutdown_event)
        )
    except NotImplementedError:
        logging.warning("Signal handlers not supported on this platform")
    
    try:
        await run_server(
            host=host,
            port=4433,
            configuration=configuration,
            shutdown_event=shutdown_event
        )
    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        logging.info("Application shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        logging.info("Application terminated")