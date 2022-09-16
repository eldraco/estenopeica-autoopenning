# Program to control a servo using the Heltec esp32 and sending telemetry to the Internet

import network
import time
from time import sleep
import os
import gc
import sys
from machine import I2C
from machine import Pin
from machine import ADC
from machine import PWM
import machine
import ssd1306
from umqtt.robust import MQTTClient
import ntptime


# Configuration of the pins of the sensor. Looking at the heltec
# it the display looking away from your eyes
# Pin GND: Is the first pin from the top right. The white cable without ribon
# Pin 5v: Is the second pin from the top right. The while cable WITH ribon
# Pin data: Is pin numbered 33 in the board. the eleventh pin from top right


# ---
## Setup the display
# Reset the pins, Not sure
rst = Pin(16, Pin.OUT)
rst.value(1)

# Setup Pin for oled
scl = Pin(15, Pin.OUT, Pin.PULL_UP)
sda = Pin(4, Pin.OUT, Pin.PULL_UP)
i2c = I2C(scl=scl, sda=sda, freq=450000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

# Set pinhole open time. 60 seconds = 1 minute
PINHOLE_OPEN_TIME = 60
# ---

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
    ADAFRUIT_IO_KEY = b''
    ADAFRUIT_IO_FEEDNAME1 = b'Sensor1-Hum'
    ADAFRUIT_IO_FEEDNAME2 = b'Pinhole'
    ADAFRUIT_IO_FEEDNAME3 = b'WaitingTime'

    client = MQTTClient(client_id=mqtt_client_id,
                        server=ADAFRUIT_IO_URL,
                        user=ADAFRUIT_USERNAME,
                        password=ADAFRUIT_IO_KEY,
                        ssl=False)
    try:
        client.connect()
    except Exception as e:
        write_display('Cant connect')
        write_display('to mqtt', line=2, clean=False)
        print('could not connect to MQTT server {}{}'.format(type(e).__name__, e))
        sys.exit()
    # Publish mqtt data
    mqtt_feedname_hum = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_FEEDNAME1), 'utf-8')
    mqtt_feedname_pinhole = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_FEEDNAME2), 'utf-8')
    mqtt_feedname_waiting = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_FEEDNAME3), 'utf-8')
    return (client, mqtt_feedname_hum, mqtt_feedname_pinhole, mqtt_feedname_waiting)

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

def take_pic(servo):
    """
    Open the pinhole
    Report to mqtt
    Wait
    Close pinhole
    """
    # Open pinhole
    write_display('Opening')
    write_display('pinhole', line=2, clean=False)

    ## Publish
    client.publish(mqtt_feedname_pinhole, bytes(str('1'), 'utf-8'), qos=0)
    ## Open it
    pinhole(servo, 'open')

    # Sleep the time to take the capture
    time.sleep(PINHOLE_OPEN_TIME)

    # Close pinhole
    write_display('Closing')
    write_display('pinhole', line=2, clean=False)
    ## Publish
    client.publish(mqtt_feedname_pinhole, bytes(str('0'), 'utf-8'), qos=0)
    ## Open
    pinhole(servo, 'close')


def get_next_opening_time(actual_time_seconds):
    """
    Given a certain time, get how much to wait until next sunday at noon 12pm
    """
    actual_time = time.localtime(actual_time_seconds)

    # Get current day of week
    actual_time_weekday = actual_time[6] 
    # Get current hour 
    actual_time_hour = actual_time[3] 

    # Hour of opening, 12 at noon
    hour_of_oppening = 12

    # Find end of current day
    # 24 - 22 = 2
    end_current_day = 24 - actual_time_hour
    
    # Find how far away is next friday. Friday is 6 in weekday numbers (Sunday = 0)
    # You decrease 1 day more because we compute the hours of the day you are separatedly
    #  On Sunday 6 - 7 = -1
    #  On Saturday 6 - 6 = 0
    #  On Friday 6 - 5 = 1
    days_diff = 6 - actual_time_weekday - 1 

    # Calculation
    # Sunday 15hs = diff = 6-6-1=-1, end current day = 9
    # Saturday 11am = diff = 6-5-1=0, end current day = 13
    # Friday 22hs : diff = 6-4-1=1, end current day = 2, 
    # Tusday 2pm = diff = 6-2-1=3, end current day = 10

    # if days_diff is <= 0, total time is 12hs - current hour
    # if days_diff is > 0, total time is + 12hs - current hour
    if days_diff == -1:
        # Sunday
        # Is pre oppening time?
        if actual_time_hour <= hour_of_oppening:
            total_hours = hour_of_oppening - actual_time_hour
        # Is post oppening time on sunday?
        # Wait 7 days + the rest of sunday
        total_hours = (7 * 24) + (24 - actual_time_hour)
    elif days_diff >= 0:
        total_hours = (days_diff * 24) + end_current_day + hour_of_oppening

    # Convert total_hours in correct time in seconds 
    total_seconds = total_hours * 60 * 60
    total_time = time.localtime(actual_time_seconds + total_seconds)

    return total_time

# Main code before the loop
# The oled first
write_display('Estenopeica')
write_display('Abuelo 2.2', line=2, clean=False)
time.sleep(1)

# Set up the wifi
setup_wifi()
time.sleep(1)

# Get the correct time and date from the Internet
ntptime.settime()
# -3 is buenos aires, argentina
UTC_OFFSET = -3 * 60 * 60
actual_time = time.localtime(time.time() + UTC_OFFSET)

# Setup humidity sensor
hum = setup_humidity_sensor()
time.sleep(1)

# Setup mqtt
client, mqtt_feedname_hum, mqtt_feedname_pinhole, mqtt_feedname_waiting = setup_mqtt()
PUBLISH_PERIOD_IN_SEC = 60
time.sleep(1)

# Setup led
#setup_led()
#time.sleep(1)

# Setup the servo
servo = setup_servo()
time.sleep(1)


write_display('Going to loop')
time.sleep(1)

# Main loop
while True:
    try:

        # As backup to cover from errors, sleep every 1hs
        waiting_time = 3600

        # Read humidity
        write_display('Reading Humidity')
        hum_value = hum.read()
        write_display('Hum '+ str(hum_value), line=2)
        client.publish(mqtt_feedname_hum, bytes(str(hum_value), 'utf-8'), qos=0)

        # - Calculate if we need to take a pic
        # Get current time
        actual_time_seconds = time.time() + UTC_OFFSET
        # positions: (year, month, mday, hour, minute, second, weekday, yearday)
        actual_time = time.localtime(actual_time_seconds)
        # Get current day of week
        actual_time_weekday = actual_time[6] 
        # Get current hour 
        actual_time_hour = actual_time[3] 
        # Get when it is going to be the next picture time. Next Sunday 12:00pm
        picture_time = get_next_opening_time(actual_time_seconds)
        write_display('Wait for pic')
        write_display(str(picture_time), line=2, clean=False)
        write_display('hs', line=3, clean=False)
        # Get current day of week
        picture_time_weekday = picture_time[6] 
        # Get current hour 
        picture_time_hour = picture_time[3] 

        # If it is the day and hour of picture. Hour is without minutes.
        if actual_time_weekday == picture_time_weekday and  actual_time_hour == picture_time_hour:
            write_display('Take Pic!')
            # Take pic
            take_pic(servo)
            # If take pics fails for some reason, we will wait until next day

        # If it is sunday and before picture time
        if actual_time_weekday == picture_time_weekday and actual_time_hour < picture_time_hour:
            # sleep every 1 hour
            waiting_time = 3600
            write_display('Waiting one')
            write_display('1 hour', line=2, clean=False)
            client.publish(mqtt_feedname_waiting, bytes(str(waiting_time), 'utf-8'), qos=0)
        # If it is not sunday or it is sunday after 12hs and at 12hs
        elif (actual_time_weekday != picture_time_weekday) or (actual_time_weekday == picture_time_weekday and actual_time_hour >= picture_time_hour):
            # Sleep for 1 day minus the time we are already away from picture time
            # This is important not to add 1 minute delays during the year
            after_pic_actual_time_seconds = time.time() + UTC_OFFSET
            diff_since_pic = after_pic_actual_time_seconds - actual_time_seconds
            waiting_time = 86400 - diff_since_pic
            write_display('Waiting one')
            write_display('1 dayish', line=2, clean=False)
            client.publish(mqtt_feedname_waiting, bytes(str(waiting_time), 'utf-8'), qos=0)
            # This is the most important sleep. We should try to wake up at 12 next day

        write_display('Sleeping...')
        time.sleep(waiting_time)
    except KeyboardInterrupt:
        print('Ctrl-C pressed...exiting')
        client.disconnect()
        sys.exit()
