import datetime
import configparser
import mysql.connector.pooling
import time
import socket
import threading
from kafka import KafkaProducer
from confluent_kafka import Consumer, KafkaException
import os
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from prometheus_client import push_to_gateway


bootstrap_servers = 'mycas-kafka-service:9092'
producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
config = configparser.ConfigParser()
config.read(r'stage_cycle.ini')

db_config = {
    "host": 'mycas-mysql-service',
    "user": "omi_user",
    "password": "omi_user",
    "database": "cas",
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="my_pool", pool_size=30, **db_config)

# Create a cursor to interact with the database
total_cycled = 0
if not os.path.exists(r'./Logs'):
    os.makedirs(r'./Logs')

registry = CollectorRegistry()
cycled = Gauge('mycas_cycler', 'cycler', registry=registry)
pushgateway_url = 'http://prometheus-pushgateway:9091'
producer = KafkaProducer(bootstrap_servers=bootstrap_servers)

cycle_osm = int(config.get(str(44), 'cycle'))
stage_osm = int(config.get(str(44), 'stage'))
cycle_adddevice = int(config.get(str(10), 'cycle'))
stage_adddevice = int(config.get(str(10), 'stage'))
cycle_entitlement = int(config.get(str(21), 'cycle'))
stage_entitlement = int(config.get(str(21), 'stage'))
topic = 'topic_cycler'

cycle_osm_metric = Gauge('cycle_osm', 'Cycle', registry=registry)
stage_osm_metric = Gauge('stage_osm', 'Stage', registry=registry)
cycle_adddevice_metric = Gauge('cycle_adddevice', 'Cycle', registry=registry)
stage_adddevice_metric = Gauge('stage_adddevice', 'Stage', registry=registry)
cycle_entitlement_metric = Gauge('cycle_entitlement', 'Cycle', registry=registry)
stage_entitlement_metric = Gauge('stage_entitlement', 'Stage', registry=registry)

# Set metric values
cycle_osm_metric.set(cycle_osm)
stage_osm_metric.set(stage_osm)
cycle_adddevice_metric.set(cycle_adddevice)
stage_adddevice_metric.set(stage_adddevice)
cycle_entitlement_metric.set(cycle_entitlement)
stage_entitlement_metric.set(stage_entitlement)

push_to_gateway(pushgateway_url, job='stage_cycle', registry=registry)


def osm():
    connection = connection_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT starttime, endtime, emmdata, emmtype FROM emmg where emmtype = 21 limit 1000")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    current_time = int(time.time())
    global total_cycled
    for row in rows:
        starttime, endtime, emmdata, emmtype = row
        stage_endtime = int(starttime + stage_osm)
    # Check if current time (in epoch) is less than end time for the emmtype
        if current_time < endtime and current_time < stage_endtime:
            message = f'{emmdata}'
            producer.send(topic, message.encode('utf-8')).get()
            total_cycled += 1
            cycled.set(total_cycled)
            push_to_gateway(pushgateway_url, job='cycled', registry=registry)
            #print(emmdata)
            #print('Cycle osm Done')
    time.sleep(cycle_osm)

def adddevice():
    global total_cycled
    connection = connection_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT starttime, endtime, emmdata, emmtype FROM emmg where emmtype = 10 limit 1000")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    current_time = int(time.time())

    for row in rows:
        starttime, endtime, emmdata, emmtype = row
        stage_endtime = int(starttime + stage_adddevice)
    # Check if current time (in epoch) is less than end time for the emmtype
        if current_time < endtime and current_time < stage_endtime:
            message = f'{emmdata}'
            producer.send(topic, message.encode('utf-8')).get()
            total_cycled += 1
            cycled.set(total_cycled)
            push_to_gateway(pushgateway_url, job='cycled', registry=registry)
            #print('Cycle adddevice Done')
    time.sleep(cycle_adddevice)

def entitlement():
    global total_cycled
    connection = connection_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT starttime, endtime, emmdata, emmtype FROM emmg where emmtype = 44 limit 1000")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    current_time = int(time.time())

    for row in rows:
        starttime, endtime, emmdata, emmtype = row
        stage_endtime = int(starttime + stage_entitlement)
        # Check if current time (in epoch) is less than end time for the emmtype
        if current_time < endtime and current_time < stage_endtime:
            message = f'{emmdata}'
            producer.send(topic, message.encode('utf-8')).get()
            total_cycled += 1
            cycled.set(total_cycled)
            push_to_gateway(pushgateway_url, job='cycled', registry=registry)
            #print('Cycle entitlement Done')

    time.sleep(cycle_entitlement)


while True:
    osm_thread = threading.Thread(target=osm)
    entitlement_thread = threading.Thread(target=entitlement)
    adddevice_thread = threading.Thread(target=adddevice)

    # Start the threads
    osm_thread.start()
    entitlement_thread.start()
    adddevice_thread.start()

    # Wait for all threads to complete
    osm_thread.join()
    entitlement_thread.join()
    adddevice_thread.join()

