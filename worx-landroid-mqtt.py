#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
   import ConfigParser as ConfigParser
except: 
   import configparser as ConfigParser

import time
import paho.mqtt.client as mqtt
import dweepy
import requests
import os

DEBUG = False
running = True

os.chdir('/home/pi/repos/worx-landroid/')

Config = ConfigParser.ConfigParser()
#Config.read('/home/pi/repos/worx-landroid/config.ini')
Config.read('config.ini')

def on_connect(client, userdata, rc):
   if(DEBUG):
      print("Connected with result code" + str(rc))

def on_message(client, userdata, msg):
   if(DEBUG):
      print("Received new message ")
      print(msg.topic + ":  " + str(msg.payload))
   #pass

# Initiate mqtt-client
mqttc = mqtt.Client()
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.connect(Config.get("Mqtt", "Host"), int(Config.get("Mqtt", "Port")), 60)
mqttc.loop_start()

def push_message(sub_topic, value):
   # Push mqtt message
   topic = Config.get("Mqtt", "BaseTopic") + sub_topic
   mqttc.publish(topic, value)
   # Dweet message
   dweepy.dweet_for(Config.get("Dweet", "Thing"), {sub_topic: str(value)})

def check_general(data):
   push_message('/battery', float(data['perc_batt']))

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
             '',
             'charge_error',
             'battery_error']

   for i in range(len(alarms)):
      if alarm_array[i]==1:
         alarm_ok = 0
         if(DEBUG):
            print(alarms[i])
      push_message('/alarm/' + alarms[i], alarm_array[i])
   
   push_message('/alarm/alarm_ok', alarm_ok)

while running:
   # Poll Landroid Worx
   response = requests.get(Config.get("Landroid", "Addr"), auth=(Config.get("Landroid", "User"),Config.get("Landroid", "Pin")))
   data = response.json()

   # Check alarm status 
   check_alarms(data['allarmi'])
   check_general(data)

   # Wait, and then exit program  
   time.sleep(2)
   mqttc.loop_stop()
   running = False
   
