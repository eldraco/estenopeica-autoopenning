# Estenopeica autoopenning
Program to control an esp32 device to open automatically an estenopeica pinhole camera


# To program
ampy -p /dev/cu.usbserial-0001 put main.py /main.py



# To see in the Internet
https://io.adafruit.com/eldraco/dashboards/estenopeica-abuelo

# Features
- WiFi connection for NTP and for reporting to Adafruit Dashboard.
    - The reconnection to the WiFi happens almost forever (2millon times) because it may happen that in rainy days or if the WiFi router is beign rebooted that you need to just keep trying.
    - The credentials for the WiFi should go in a file called `wifi-credentials.txt` with the format:
        ```
        WIFI_SSID = 'essid'
        WIFI_PASSWORD = 'password'
        ```
- Sends MQTT data to a dashboard in [adafruit](https://io.adafruit.com/). You need to put your token.
    - The credentials ˙˙
- Uses an OLED display to show information about the state.
- It implements a poor's man humidity sensor by checking the voltage between two adjacent pins in the Heltec. This is not super good, but is something that varies with humidity. So...
- Uses a servo to move the door of the `estenopo` (door of the camera hole)

# How does it work?
- Waits until is the day configured to open. The program uses NTP to syncrhonize the exact date, so it know which day is it, like Monday, etc.
    - So you can specify if you want to open on Tuesdays, or Sundays.
    - Check your timezone and update the variable `UTC_OFFSET`.
- The program wakes up every 1hs and does some checking and reporting, such as the humidity. This is so you have a feedback that everything is working correctly and you dont have to wait until opening time to check.
- Waits until it is the time to open. Also configured in the python file. By default at 12hs (noon).
- The pinhole opens by default for 2 minutes (configuration in python)
- Since the program runs every 1hs, does something and waits another 1hs, how does it know if the opening time is in 45 mins? Well we calculate the difference in time and just wait exactly what we need if it is less than 1hs.
