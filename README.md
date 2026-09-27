# QUIC IoT Telemetry Streamer

A Python-based transport layer for streaming real-time IoT sensor data. By leveraging the QUIC protocol (`aioquic`), this project bypasses common TCP bottlenecks (like Head-of-Line blocking) to ensure low-latency, high-frequency data delivery over unstable networks.

## System Architecture

The project is split into two main components:

1. **The Server (Base Station / Cloud)**
   - Designed to run on a centralized cloud instance or local base station.
   - Listens for incoming QUIC streams, processes the high-frequency telemetry, and logs real-time throughput and performance metrics.
2. **The Client (IoT Edge Device)**
   - Designed to run on an edge device (e.g., Raspberry Pi, Jetson) attached to a moving object.
   - **Hardware Connection:** The client physically connects to an IMU sensor via USB serial port (`/dev/ttyACM0`). It reads the raw sensor data and multiplexes it over QUIC to the server.
   - **Demo Mode (No Hardware Required):** If you are just testing the software and do not have a physical IMU plugged in, the client will gracefully fall back to generating high-frequency mock data (~500 Hz). This makes it easy to test the transport layer out-of-the-box!

---

## 📊 Performance Benchmarks & Research Highlights

Based on empirical testing (detailed in `Analysis of Transport over QUIC.pdf`), this transport layer was benchmarked for high-frequency IMU telemetry against traditional TCP:

- **Throughput Supremacy**: The prioritized QUIC multi-stream configuration achieved **~395 msgs/sec**, outperforming the TCP implementation (340 msgs/sec) by **16%**.
- **Head-of-Line Blocking Mitigation**: Unlike TCP, which suffered from throughput fluctuations during network instability, QUIC's independent stream multiplexing provided significantly steadier delivery rates.
- **Custom Prioritization**: By writing custom byte-scheduling algorithms over `aioquic`, critical telemetry (Accelerometer) consistently preempted lower-priority sensor data without blocking the connection.
- **Security Implications**: Despite QUIC's native TLS 1.3 encryption, side-channel metadata analysis (burst sizes) can still leak application-layer context with 93% accuracy.

---

## Installation & Quickstart (Docker) - Recommended

The easiest way to test the system is via Docker. This allows you to simulate both the Server and the Client on your local machine without needing to install any Python dependencies.

1. **Start the QUIC Server (Base Station):**
   This spins up the server in the background and automatically generates local SSL certificates.
   ```bash
   docker-compose up -d --build
   ```

2. **Start the QUIC Client (IoT Device):**
   Run the client directly inside the isolated container. Because you likely don't have an IMU sensor plugged into your laptop, it will automatically use Demo Mode and generate mock data.
   ```bash
   docker exec -it quic-iot_quic-server_1 python3 quic_client.py --host local --stream single
   ```

3. **View live throughput logs:**
   Open a new terminal and watch the server actively ingest the high-frequency stream:
   ```bash
   tail -f logs/quic_server.log
   ```

---

## Installation & Running (Manual / From Source)

If you prefer to run the system natively without Docker, follow these instructions.

### Requirements

Install dependencies using:

```bash
pip install -r requirements.txt
```

### SSL Certificates

To generate a self-signed certificate and private key for local development, run the included script:

```bash
./generate_certs.sh
```

### QUIC Server

Run with:

```bash
python quic_server.py --host [local|server]
```

- `local`: Binds to `127.0.0.1` (IPv4 localhost)
- `server`: Binds to `0.0.0.0` for external access

### QUIC Client

Run with:

```bash
python quic_client.py --host [local|server] --stream [single|multi|no_priority]
```

- `--host`:
  - `local`: Connects to `127.0.0.1`
  - `server`: Connects to remote server IP (configured in `.env`)
- `--stream`:
  - `single`: Streams both accelerometer and gyroscope over a single QUIC stream
  - `multi`: Uses separate streams with custom prioritization (edit weights in `quic_client.py`)
  - `no_priority`: Separate streams with FIFO scheduling

### TCP Server and Client

Run TCP server:
```bash
python tcp_server.py --host [local|server]
```

Run TCP client:
```bash
python tcp_client.py --host [local|server]
```

---

## Notes

- For real deployment, use secure SSL certificates from a trusted CA.
- Prioritization in `quic_client.py` can be fine-tuned using weight variables.
- Tested with Python 3.13
