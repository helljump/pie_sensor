# pie_sensor

sensors.py is the app that obtains data from 433Mhz weather, motion and smoke sensors.
It works via wl433 connected to GPIO Raspeberry PI pins.
Supported protocol is Nexus. It means few Digoo sensors work with the app.

![Connected pins](pie-pinout.png)

![Reciever](wl433.png)

The app sends data to MQTT broker like Moquitto.

In additional there is desktop app mqttmon.py that uses GTK3 to display information fetched from MQTT broker.

![MQTTMon](mqttmon.png)

