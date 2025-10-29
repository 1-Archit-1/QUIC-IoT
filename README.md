# IMU Streaming Server and Client

This repository provides implementations of both QUIC and TCP-based streaming servers and clients for Inertial Measurement Unit (IMU) data, including accelerometer and gyroscope streams.

Check https://github.com/1-Archit-1/QUIC-Streaming for Media implementaion and https://github.com/1-Archit-1/WebTransport-Client-Server for Basic Client-Server code. 

## 📦 Features

- **QUIC and TCP support** for low-latency data streaming
- **Multiple streaming modes**: single-stream and multi-stream IMU data handling
- **Custom prioritization** for QUIC multi-stream modes
- **SSL certificate support** (sample certs included)
- **Runtime logs** provide performance and throughput stats

---

## 🧪 Requirements

Install dependencies using:

```bash
pip install -r requirements.txt
```

---

## 🚀 QUIC Server

Run with:

```bash
python quic_server.py --host [local|server]
```

- `local`: Binds to `localhost`
- `server`: Binds to `0.0.0.0` for external access

### 🔐 SSL Certificates

Sample self-signed certificates are provided (`cert.pem` and `key.pem`) **for development only**.

To generate your own for production:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

You’ll be prompted for certificate details (country, organization, etc.).

---

## 📡 QUIC Client

Run with:

```bash
python quic_client.py --host [local|server] --stream [single|multi|no_priority]
```

- `--host`:
  - `local`: Connects to `localhost`
  - `server`: Connects to remote server IP (edit inside `quic_client.py`)
- `--stream`:
  - `single`: Streams both accelerometer and gyroscope over a single QUIC stream
  - `multi`: Uses separate streams with custom prioritization (edit weights in `quic_client.py`)
  - `no_priority`: Separate streams with FIFO scheduling

---

## 🌐 TCP Server

Run with:

```bash
python tcp_server.py --host [local|server]
```

---

## 🔌 TCP Client

Run with:

```bash
python tcp_client.py --host [local|server]
```

---

## 📊 Logs

Logs contain runtime statistics
---

---

## 📌 Notes

- For real deployment, use secure SSL certificates from a trusted CA.
- Prioritization in `quic_client.py` can be fine-tuned using weight variables.
- Tested with Python 3.13
- 
