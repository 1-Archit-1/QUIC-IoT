FROM python:3.13-slim

WORKDIR /app

# Install openssl for certificate generation
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure certificates exist
RUN chmod +x generate_certs.sh && ./generate_certs.sh

# Expose QUIC (UDP) and TCP ports
EXPOSE 4433/udp
EXPOSE 5555/tcp

CMD ["python", "quic_server.py", "--host", "server"]
