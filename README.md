# IMU Streaming Server and Client

This repository provides implementations of both QUIC and TCP-based streaming servers and clients for Inertial Measurement Unit (IMU) data, including accelerometer and gyroscope streams.

Check https://github.com/1-Archit-1/QUIC-Streaming for Media implementaion and https://github.com/1-Archit-1/WebTransport-Client-Server for Basic Client-Server code. 

## Features

- **QUIC and TCP support** for low-latency data streaming
- **Multiple streaming modes**: single-stream and multi-stream IMU data handling
- **Custom prioritization** for QUIC multi-stream modes
- **SSL certificate support** (sample certs included)
- **Runtime logs** provide performance and throughput stats

---

## Performance Benchmarks & Research Highlights

Based on empirical testing (detailed in `Analysis of Transport over QUIC.pdf`), this transport layer was benchmarked for high-frequency IMU telemetry against traditional TCP:

- **Throughput Supremacy**: The prioritized QUIC multi-stream configuration achieved **~395 msgs/sec**, outperforming the TCP implementation (340 msgs/sec) by **16%**.
- **Head-of-Line Blocking Mitigation**: Unlike TCP, which suffered from throughput fluctuations during network instability, QUIC's independent stream multiplexing provided significantly steadier delivery rates.
- **Custom Prioritization**: By writing custom byte-scheduling algorithms over `aioquic`, critical telemetry (Accelerometer) consistently preempted lower-priority sensor data without blocking the connection.
- **Security Implications**: Despite QUIC's native TLS 1.3 encryption, side-channel metadata analysis (burst sizes) can still leak application-layer context with 93% accuracy.

---

## Hardware Fallback & Data Generation

The IMU client is designed to stream physical telemetry data by searching for a real IMU hardware device connected via serial port at `/dev/ttyACM0`. 

If a physical IMU is not detected on that port, the system automatically falls back to generating high-frequency mock data (~500 Hz). This ensures the repository works instantly out-of-the-box for testing and demonstration purposes without requiring physical hardware.

---

## Installation & Running (Docker) - Recommended

The easiest way to run the QUIC server and its dependencies is via Docker. The Dockerfile will automatically install all Python dependencies and generate the required local SSL certificates.

1. **Start the QUIC server:**
   ```bash
   docker-compose up -d --build
   ```

2. **Test the streaming client:**
   Since the server is isolated in the container, you can run the client directly inside the running container to stream data (this avoids needing to install dependencies on your local machine):
   ```bash
   docker exec -it quic-iot_quic-server_1 python3 quic_client.py --host local --stream single
   ```

3. **View live throughput logs:**
   Because the logs are volume-mounted, you can watch the streaming metrics in real-time on your host machine:
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

Or manually:
```bash
openssl req -x509 -newkey rsa:4096 -keyout ssl_key.pem -out ssl_cert.pem -sha256 -days 365 -nodes
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
