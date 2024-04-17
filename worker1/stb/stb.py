import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from confluent_kafka import Consumer, KafkaException
import socket
import struct
import sys
import pyaes
import base64
import time
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from confluent_kafka import Consumer, KafkaException, KafkaError

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    datefmt='%d-%m-%Y:%H:%M:%S',
    level=logging.DEBUG,
    handlers=[
        TimedRotatingFileHandler(
            filename='./Logs/stb.log',
            backupCount=10,
            when='midnight',
            interval=1
        )
    ]
)


internal_logger = logging.getLogger('werkzeug._internal')
internal_logger.setLevel(logging.DEBUG)

kafka_logger = logging.getLogger('kafka')
kafka_logger.setLevel(logging.DEBUG)


# Define Kafka consumer configuration
conf = {
    'bootstrap.servers': 'mycas-kafka-service:9092',
    'group.id': 'emmg',
    'auto.offset.reset': 'earliest'
}

# Initialize Kafka consumer
consumer = Consumer(conf)

# Subscribe to the topic
topic = 'topic_cycler'
consumer.subscribe([topic])
msg = consumer.poll(timeout=1.0)

# AES encryption key
key = 'qwertyuioplkjhgd'

# Initialize metrics
start_time = time.time()
total_bytes = 0
registry = CollectorRegistry()
emmbw = Gauge('mycas_emmbw', 'EMM BW in Kbps', registry=registry)
pushgateway_url = 'http://prometheus-pushgateway:9091'


# Function to decrypt string
def decrypt_string(key, encrypted_data):
    block_size = 16
    iv = pyaes.Counter(initial_value=0)
    cipher = pyaes.AESModeOfOperationCTR(key.encode('utf-8'), counter=iv)
    ciphertext = base64.b64decode(encrypted_data)
    padded_plaintext = cipher.decrypt(ciphertext).decode('utf-8')
    padding_length = ord(padded_plaintext[-1])
    plaintext = padded_plaintext[:-padding_length]
    #logging.info(plaintext)  # Log decrypted plaintext
    return plaintext


# Function to start receiving messages
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
                if msg.error().code() == KafkaError._OFFSET_OUT_OF_RANGE:
                    consumer.seek(topic, partition, 0)
                    continue
                else:
                    # Log other errors
                    logging.error(f"Error: {msg.error().str()}")
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
                    logging.info(columns[2])  # Log columns[2] value
                    #print(columns[2])  # Print columns[2] value
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt: Closing socket.")
        sys.exit(0)

if __name__ == '__main__':
    start_receiving()
