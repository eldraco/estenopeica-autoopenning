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


## Setup the display
# Reset the pins
# Not sure
rst = Pin(16, Pin.OUT)
rst.value(1)

def write_display(text, line=1, clean=True):
    """
    Write in the oled dispaly
    """
    if clean:
        oled.fill(0)
    # Separation from left side, 5 pixels
    x = 5
    y = (line - 1) * 10
    oled.text(text, x, y)
    oled.show()

# Setup Pin for oled
scl = Pin(15, Pin.OUT, Pin.PULL_UP)
sda = Pin(4, Pin.OUT, Pin.PULL_UP)
i2c = I2C(scl=scl, sda=sda, freq=450000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)



def setup_wifi():
    """
    Setup the wifi
    """
    write_display('Setting up wifi')
    # Setup the WiFi connection information
    WIFI_SSID = 'Fibertel WiFi931 2.4GHz'
    WIFI_PASSWORD = '0044384846'

    # turn off the WiFi Access Point, just in case
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)

    write_display('Connecting with', line=2, clean=False)
    write_display(WIFI_SSID, line=3, clean=False)

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
        print('Could not connect to the WiFi network.')
        write_display('Could not connect', line=4, clean=False)
        write_display('to Wifi', line=5, clean=False)
        sys.exit()

    write_display('Connected.', line=4, clean=False)


def setup_mqtt():
    """
    Setup mqtt
    """
    write_display('Setting mqtt')
    # Create a random MQTT clientID
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
    return (client, mqtt_feedname)


def setup_led():
    """
    Setup led
    """
    write_display('Setting up')
    write_display('led', line=2, clean=False)
    # Blink led to show that is working
    led = Pin(25, Pin.OUT)
    for i in range(2):
        led.on()
        sleep(500)
        led.off()
        sleep(500)

def setup_humidity_sensor():
    """
    Setup humidity sensor
    """
    write_display('Setting up')
    write_display('humidity sensor', line=2, clean=False)
    # Pin for Analog value read of the humid sensor
    # Pin 33 in the heltec is the input
    hum = ADC(Pin(33))
    # Full range: 3.3v
    hum.atten(ADC.ATTN_11DB)
    return hum

def setup_servo():
    """
    Setup the servo
    """
    write_display('Setting up')
    write_display('Servo', line=2, clean=False)
    servopin = Pin(17)
    servo = PWM(servopin, freq=50)
    # Close it
    servo.duty(35)
    # First border is duty=10
    # Center is duty=35 this is closing the hole
    # Center is duty=55 this is opening the hole
    # Last border is duty=70
    return servo

def pinhole(servo, action):
    """
    Open and close the pinhole
    """
    if action == 'open':
        write_display('Opening')
        write_display('Pinhole', line=2, clean=False)
        servo.duty(55)
        write_display('Open', line=3, clean=False)
    elif action == 'close':
        write_display('Opening')
        write_display('Pinhole', line=2, clean=False)
        servo.duty(35)
        write_display('Open', line=3, clean=False)


# Main code before the loop
# The oled first
write_display('Estenopeica')
write_display('Abuelo 2.2', line=2, clean=False)
time.sleep(1)

# Set up the wifi
setup_wifi()
time.sleep(1)

# Setup humidity sensor
hum = setup_humidity_sensor()
time.sleep(1)

# Setup mqtt
client, mqtt_feedname = setup_mqtt()
PUBLISH_PERIOD_IN_SEC = 5
time.sleep(1)

# Setup led
#setup_led()
#time.sleep(1)

# Setup the servo
servo = setup_servo()
time.sleep(1)

# Test servo
pinhole(servo, 'open')
time.sleep(10)
pinhole(servo, 'close')


write_display('Going to loop')
time.sleep(1)

# Main loop
while True:
    try:
        write_display('Reading Humidity')
        hum_value = hum.read()
        write_display('Hum ', line=2)
        write_display('     ' + str(hum_value), line=2, clean=False)
        client.publish(mqtt_feedname,
                       bytes(str(hum_value), 'utf-8'),
                       qos=0)
        time.sleep(PUBLISH_PERIOD_IN_SEC)
    except KeyboardInterrupt:
        print('Ctrl-C pressed...exiting')
        client.disconnect()
        sys.exit()
