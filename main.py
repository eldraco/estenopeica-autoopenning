# Program to control a servo using the Heltec esp32 and sending telemetry to the Internet

import network
import time
import os
import gc
import sys
from machine import I2C
from machine import Pin
from machine import ADC
from machine import PWM
import machine
import ssd1306
from time import sleep
from umqtt.robust import MQTTClient


# Configuration of the pins of the sensor. Looking at the heltec
# it the display looking away from your eyes
# Pin GND: Is the first pin from the top right. The white cable without ribon
# Pin 5v: Is the second pin from the top right. The while cable WITH ribon
# Pin data: Is pin numbered 33 in the board. the eleventh pin from top right


## General setup
# WiFi connection information
WIFI_SSID = 'Fibertel WiFi931 2.4GHz'
WIFI_PASSWORD = '0044384846'

# turn off the WiFi Access Point, just in case
ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)

# connect the device to the WiFi network
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASSWORD)

# wait until the device is connected to the WiFi network
MAX_ATTEMPTS = 20
attempt_count = 0
while not wifi.isconnected() and attempt_count < MAX_ATTEMPTS:
    attempt_count += 1
    time.sleep(1)

if attempt_count == MAX_ATTEMPTS:
    print('could not connect to the WiFi network.')
    sys.exit()

# Reset the pins
# Not sure
rst = Pin(16, Pin.OUT)
rst.value(1)




# create a random MQTT clientID
random_num = int.from_bytes(os.urandom(3), 'little')
mqtt_client_id = bytes('client_'+str(random_num), 'utf-8')

# connect to Adafruit IO MQTT broker using unsecure TCP (port 1883)
# To use a secure connection (encrypted) with TLS:
#   set MQTTClient initializer parameter to "ssl=True"
#   Caveat: a secure connection uses about 9k bytes of the heap
#         (about 1/4 of the micropython heap on the ESP8266 platform)
ADAFRUIT_IO_URL = b'io.adafruit.com'
ADAFRUIT_USERNAME = b'eldraco'
ADAFRUIT_IO_KEY = b'aio_tyoZ74JecmBOiwucWCBaclFDVzip'
ADAFRUIT_IO_FEEDNAME = b'Sensor1-Hum'

client = MQTTClient(client_id=mqtt_client_id,
                    server=ADAFRUIT_IO_URL,
                    user=ADAFRUIT_USERNAME,
                    password=ADAFRUIT_IO_KEY,
                    ssl=False)
try:
    client.connect()
except Exception as e:
    print('could not connect to MQTT server {}{}'.format(type(e).__name__, e))
    sys.exit()
# Publish mqtt data
mqtt_feedname = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_FEEDNAME), 'utf-8')
PUBLISH_PERIOD_IN_SEC = 5



# Pin for oled
scl = Pin(15, Pin.OUT, Pin.PULL_UP)
sda = Pin(4, Pin.OUT, Pin.PULL_UP)
i2c = I2C(scl=scl, sda=sda, freq=450000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

# The oled first test
oled.fill(0)
oled.text('Estenopeica', 20, 5)
oled.text('Abuelo 2.0', 20, 20)
oled.show()

# Blink led to show that is working
led = Pin(25, Pin.OUT)
for i in range(2):
    led.on()
    sleep(500)
    led.off()
    sleep(500)

"""
# Test the servo
servopin = Pin(15)
servo = PWM(servopin, freq=50)
servo.duty(40)
time.sleep(0.1)
servo.duty(50)
time.sleep(0.1)
servo.duty(100)
time.sleep(0.1)
servo.duty(110)
"""

# Pin for Analog value read of the humid sensor
# Pin 33 in the heltec is the input
hum = ADC(Pin(33))
# Full range: 3.3v
hum.atten(ADC.ATTN_11DB)

# Main loop
while True:
    try:
        hum_value = hum.read()
        client.publish(mqtt_feedname,
                       bytes(str(hum_value), 'utf-8'),
                       qos=0)
        oled.fill(0)
        oled.text('Hum: ', 10, 30)
        oled.text(str(hum_value), 40, 30)
        oled.show()
        time.sleep(PUBLISH_PERIOD_IN_SEC)
    except KeyboardInterrupt:
        print('Ctrl-C pressed...exiting')
        client.disconnect()
        sys.exit()
