#!/bin/bash

# Script to generate a self-signed certificate and private key for local testing

echo "Generating self-signed certificate (ssl_cert.pem) and private key (ssl_key.pem)..."
openssl req -x509 -newkey rsa:4096 -keyout ssl_key.pem -out ssl_cert.pem -sha256 -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

echo "Certificates generated successfully!"
