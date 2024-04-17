from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import socket
import struct
import sys
import pyaes
import base64
import time
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from confluent_kafka import Consumer, KafkaException, KafkaError

app = Flask(__name__)

key = 'qwertyuioplkjhgd'
start_time = time.time()
total_bytes = 0
registry = CollectorRegistry()
emmbw = Gauge('mycas_emmbw', 'EMM BW in Kbps', registry=registry)
pushgateway_url = 'http://prometheus-pushgateway:9091'

conf = {
    'bootstrap.servers': 'mycas-kafka-service:9092',
    'group.id': 'emmg',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(conf)

# Subscribe to the topic
topic = 'topic_cycler'
consumer.subscribe([topic])
msg = consumer.poll(timeout=1.0)
#print(msg.value().decode('utf-8'))


# Create an AES cipher object with the provided key and CTR mode
def decrypt_string(key, encrypted_data):
    block_size = 16
    iv = pyaes.Counter(initial_value=0)
    cipher = pyaes.AESModeOfOperationCTR(key.encode('utf-8'), counter=iv)
    ciphertext = base64.b64decode(encrypted_data)
    padded_plaintext = cipher.decrypt(ciphertext).decode('utf-8')
    padding_length = ord(padded_plaintext[-1])
    plaintext = padded_plaintext[:-padding_length]
    return plaintext


def start_receiving():
    global total_bytes
    global start_time
    try:
        while True:
            # Poll for messages
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue
            elif msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # Reached end of partition, continue to next partition
                    continue
                else:
                    # Handle other errors
                    print(f"Error: {msg.error().str()}")
                    break
            else:
                data = msg.value().decode('utf-8')
                plaintext = decrypt_string(key, data)
                total_bytes += len(data)

                elapsed_time = time.time() - start_time
                if elapsed_time >= 30:
                    bytes_per_sec = (total_bytes / elapsed_time) / 1024
                    emmbw.set(bytes_per_sec)
                    push_to_gateway(pushgateway_url, job='cycler', registry=registry)
                    total_bytes = 0
                    start_time = time.time()

                columns = plaintext.split(':')
                if columns[0] == '7010000001' and (columns[3] == '21' or columns[3] == '44'):
                    print(columns[2])
    except KeyboardInterrupt:
        print("KeyboardInterrupt: Closing socket.")
        sys.exit(0)

if __name__ == '__main__':
    start_receiving()
