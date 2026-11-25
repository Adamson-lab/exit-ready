import psycopg2, redis
from kafka import KafkaProducer

def save(x):
    return psycopg2.connect('...').cursor().execute('insert', x)
