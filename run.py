#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    import ConfigParser as ConfigParser
except:
    import configparser as ConfigParser

import time
import paho.mqtt.client as mqtt
import requests
import os

DEBUG = True
running = True

os.chdir(os.path.dirname(os.path.abspath(__file__)))

Config = ConfigParser.ConfigParser()
Config.read('config.ini')


def on_connect(self, client, userdata, rc):
    debug_print("Connected with result code" + str(rc))
    self.subscribe(Config.get("Mqtt", "BaseTopic") + '/command/#')


def on_message(client, userdata, msg):
    debug_print("Received new message ")
    debug_print(msg.topic + ":  " + str(msg.payload))
    command = msg.payload.decode("utf-8").lower()
    handle_command(command)


def debug_print(message):
    if DEBUG:
        print(message)


def handle_command(command):
    if 'start' == command:
        debug_print("Sending start...")
        send_command(11)
    elif 'stop' == command:
        debug_print("Not implemented!")
    elif 'gohome' == command:
        debug_print("Sending gohome...")
        send_command(12)
    elif 'check' == command:
        debug_print("Sending check...")
        send_check()
    else:
        debug_print("Unknown command!")


def send_command(command):
    try:
        url = Config.get("Landroid", "Addr")
        auth = (Config.get("Landroid", "User"), Config.get("Landroid", "Pin"))
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/plain'}
        data = 'data=[["settaggi",{},1]]'.format(str(command))
        response = requests.post(url, auth=auth, headers=headers, data=data)
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        print("Connection timeout")
    except requests.exceptions.RequestException:
        print("Connection error")


def send_check():
    try:
        response = requests.get(Config.get("Landroid", "Addr"), auth=(Config.get("Landroid", "User"),Config.get("Landroid", "Pin")), timeout=5)
        data = response.json()
        # Check alarm status
        check_alarms(data['allarmi'])
        check_general(data)
        debug_print(data)
    except requests.exceptions.Timeout:
        print("Connection timeout")
    except requests.exceptions.RequestException:
        print("Connection error")
        push_message('/status', 'no connection')

def push_message(sub_topic, value):
    # Push mqtt message
    topic = Config.get("Mqtt", "BaseTopic") + sub_topic
    mqttc.publish(topic, value)


def check_general(data):
    push_message('/battery', float(data['perc_batt']))
    if data['batteryChargerState'] == "charging":
      push_message('/status', (data['batteryChargerState']))
    else:
      push_message('/status', (data['state']))
    push_message('/distance', float(data['distance'])/1000)
    if data['state'] == "home" or data['state'] == "idle":
      push_message('/commandstatus', "gohome")
    else:
      push_message('/commandstatus', "start")
    push_message('/workorder', (data['workReq']))
    push_message('/message', (data['message']))
    push_message('/workarea', (data['area_in_lavoro']))

def check_alarms(alarm_array):
    alarm_ok = 1
    alarms = ['blade_blocked',
              'repositioning_error',
              'outside_wire',
              'blade_blocked',
              'outside_wire',
              'mower_tilted',
              'error',
              'error',
              'error',
              'collision_sensor_blocked',
              'mower_tilted',
              'charge_error',
              'battery_error']

    for i in range(len(alarms)):
        if alarm_array[i]==1:
            alarm_ok = 0
            debug_print(alarms[i])
        push_message('/alarm/' + alarms[i], alarm_array[i])

    push_message('/alarm/alarm_ok', alarm_ok)


# Initiate mqtt-client
mqttc = mqtt.Client()
if Config.get("Mqtt", "Authentication") == "yes":
  mqttc.username_pw_set(Config.get("Mqtt", "User"), Config.get("Mqtt", "Password"))
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.connect(Config.get("Mqtt", "Host"), int(Config.get("Mqtt", "Port")), 30)
mqttc.loop_start()

# Continuous automatic checking
while 1:
  if Config.get("Mqtt", "Autocheck") == "yes":
    send_check()
    time.sleep(float(Config.get("Mqtt", "Interval")))
  else:
    time.sleep(60)
