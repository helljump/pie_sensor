#!/usr/bin/env python3

import logging
import time
from RPi import GPIO
import paho.mqtt.client as mqtt
import json


MQTT_IP = '127.0.0.1'
MQTT_PORT = 1883

PIN = 27
GPIO.setmode(GPIO.BCM)
mqttc = mqtt.Client()


logging.basicConfig(level=logging.DEBUG, 
                    format='[%(asctime)s] %(levelname)-8s %(message)s')


def get_int(arr, start, finish):
    egg = arr[start:finish+1]
    spam = 0
    for v in egg:
        spam <<= 1
        spam |= v
    return spam


def get_sint(arr, start, finish):
    egg = arr[start:finish+1]
    neg = egg[0] == 1
    spam = 0
    for v in egg:
        spam <<= 1
        if neg:
            spam |= 1^v
        else:
            spam |= v
    if neg:
        spam += 1
        spam *= -1
    return spam


def fuzzy_cmp(v, std):
    dv = 0.25 * std
    return std - dv < v < std + dv


def test_nexus(timings):
    if (len(timings) - 2) // 2 != 36:
        return
    egg = timings[-2]
    if not fuzzy_cmp(egg, 500):
        logging.debug('nexus wrong sync pulse %i', egg)
        return
    egg = timings[-1]
    if not fuzzy_cmp(egg, 4000):
        logging.debug('nexus wrong sync length %i', egg)
        return
    acc = list()
    for i in range(0, len(timings)-2, 2):
        if not fuzzy_cmp(timings[i], 480):
            logging.debug('nexus wrong pulse size %i', timings[i])
            return
        if fuzzy_cmp(timings[i+1], 1000):
            acc.append(0)
        elif fuzzy_cmp(timings[i+1], 2000):
            acc.append(1)
        else:
            logging.debug('nexus wrong value %i', timings[i+1])
            pass
    _id = get_int(acc, 0, 7)
    batt = get_int(acc, 8, 8)
    chan = get_int(acc, 10, 11) + 1
    temp = get_sint(acc, 14, 23) / 10
    hum = get_int(acc, 28, 35)
    payload = dict(
        battery=batt,
        temperature=temp,
        humidity=hum
    )
    logging.debug('nexus:%i/%i t:%.1f h:%.1f', _id, chan, temp, hum)
    mqttc.connect('127.0.0.1', 1883)
    rc = mqttc.publish('temp/%i/%i' % (_id, chan), json.dumps(payload))
    mqttc.disconnect()
    logging.debug('sending rc %s', rc)


def test_alarm(timings):
    sub_timings = timings[0:-1]
    if len(sub_timings) // 2 != 24:
        return
    egg = timings[-2]
    if not fuzzy_cmp(egg, 400):
        logging.debug('alarm wrong sync pulse %i', egg)
        return
    egg = timings[-1]
    if not fuzzy_cmp(egg, 13000):
        logging.debug('alarm wrong sync length %i', egg)
        return
    acc = list()
    for i in range(0, len(sub_timings)-2, 4):
        if sub_timings[i] < 1000 and sub_timings[i+2] < 1000:
            acc.append('0')
        elif sub_timings[i] > 1000 and sub_timings[i+2] < 1000:
            acc.append('X')
        elif sub_timings[i] < 1000 and sub_timings[i+2] > 1000:
            acc.append('Z')
        elif sub_timings[i] > 1000 and sub_timings[i+2] > 1000:
            acc.append('1')
        else:
            raise('error')
    bits = list()
    for i in range(0, len(sub_timings), 2):
        if sub_timings[i] < 1000:
            bits.append(0)
        elif sub_timings[i] > 1000:
            bits.append(1)
    _id = get_int(bits, 0, 15)
    cmd = get_int(bits, 16, 23)
    logging.debug('alarm:%i cmd:%i tri:%s', _id, cmd, ''.join(acc))
    payload = dict(
        tri=''.join(acc),
        cmd=cmd
    )
    mqttc.connect(MQTT_IP, MQTT_PORT)
    rc = mqttc.publish('alarm/%i' % _id, json.dumps(payload))
    mqttc.disconnect()
    logging.debug('sending rc %s', rc)


class Receiver(object):

    def __init__(self):
        GPIO.setup(PIN, GPIO.IN)
        GPIO.add_event_detect(PIN, GPIO.BOTH)
        GPIO.add_event_callback(PIN, self.cb)
        self.acc = []
        self.last = int(time.perf_counter() * 1000000)
        self.recording = False
        self.sync = 3501

    def shutdown(self):
        GPIO.remove_event_detect(PIN)
        GPIO.cleanup()

    def process(self):
        while True:
            time.sleep(0.01)
            tm = int(time.perf_counter() * 1000000)
            dur = tm - self.last
            if dur > 20000:
                self.acc.clear()
                self.recording = False

    def cb(self, gpio):
        tm = int(time.perf_counter() * 1000000)
        dur = tm - self.last
        if self.recording:
            self.acc.append(dur)
            if len(self.acc) > 256:
                self.acc.clear()
                self.recording = False
        if 100 > dur > 20000:
            self.acc.clear()
            self.recording = False
        if dur > 3500 :
            if not self.recording:
                self.recording = True
                self.sync = dur
            elif dur > self.sync - 100:
                self.recording = False
                if len(self.acc) > 32:
                    test_nexus(self.acc)
                    test_alarm(self.acc)
                self.acc.clear()
        self.last = tm


rc = Receiver()
try:
    rc.process()
except:
    pass
rc.shutdown()
