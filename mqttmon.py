#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import logging
import logging.handlers
from json import loads
from json.decoder import JSONDecodeError
from datetime import datetime, timedelta
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


logger = logging.getLogger('mylogger')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address='/dev/log')
logger.addHandler(handler)


MQTT_IP = '192.168.1.10'
MQTT_PORT = 1883

COLOR_NORMAL = '#404040'
COLOR_GREEN = '#008000'
COLOR_RED = '#800000'


class Indicator(Gtk.Label):

    def __init__(self):
        super().__init__()


class Bulb(Indicator):

    def __init__(self, text, cmd):
        super().__init__()
        self.text = text
        self.cmd = cmd
        self.set_text(self.text)

    def draw(self, payload):
        try:
            arr = loads(payload)
            cmd = arr.get('cmd', 0)
            c = COLOR_RED if cmd == self.cmd else COLOR_NORMAL
            self.set_markup("<span background='%s'>%s</span>" % (c, self.text))
        except JSONDecodeError:
            pass


class Status(Indicator):

    def __init__(self, text):
        super().__init__()
        self.text = text
        self.set_text(self.text)

    def draw(self, payload):
        fc = '#ffffff' if payload == '#404040' else '#000000'
        self.set_markup("<span color='%s' background='%s'>%s</span>" % (fc, 
                        payload or COLOR_NORMAL, self.text))


class Sensor(Indicator):

    def __init__(self, title, color):
        super().__init__()
        self.title = title
        self.color = color
        self.set_markup("<span color='%s'>%s</span> %s" % (self.color, 
                                                           self.title, '___'))

    def draw(self, payload):
        try:
            arr = loads(payload)
            temp = "%s°" % arr.get('temperature', '_')
            self.set_markup("<span color='%s'>%s</span> %s" % (self.color, 
                                                               self.title, 
                                                               temp))
        except JSONDecodeError:
            pass


class AppWindow(Gtk.Window):

    def __init__(self):
        super().__init__(title="MQTTMON")
        self.set_role('toolbox')
        self.set_resizable(False)
        self.set_decorated(False)
        self.connect("destroy", self.on_destroy)

        self.set_border_width(3)
        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        vbox.set_homogeneous(False)

        self.clock = Gtk.Label()
        dt = datetime.now()
        self.clock.set_markup("<span color='#ff0000'>%s</span>" % 
                              dt.strftime('%H:%M'))
        vbox.pack_start(self.clock, True, True, 2)

        self.indicators = {
            'alarm/10': Bulb('Motion', 100),
            'alarm/20': Bulb('Smoke', 120),
            'temp/10/1': Sensor('Internal', '#94cc24'),
            'temp/20/2': Sensor('External', '#3683fb'),
        }

        for k, v in self.indicators.items():
            vbox.pack_start(v, True, True, 2)

        self.add(vbox)

        w, h = self.get_size()
        self.move(0, 1440)

        self.mqttc = mqtt.Client()
        self.mqttc.connect(MQTT_IP, MQTT_PORT)
        self.mqttc.subscribe('#')
        self.mqttc.on_message = self.on_message
        self.mqttc.loop_start()

        self.last_update = datetime(2000, 1, 1)
        GLib.timeout_add(1000, self.update_gui)

    def update_gui(self):
        dt = datetime.now()
        if dt - self.last_update > timedelta(seconds=120):
            self.clock.set_markup("<span color='#ff0000'>%s</span>" % 
                                  dt.strftime('%H:%M'))
        if dt - self.last_update > timedelta(seconds=10):
            for ind in self.indicators.values():
                if isinstance(ind, Bulb):
                    ind.draw('{}')
        return True

    def on_message(self, client, userdata, msg):
        try:
            dt = datetime.now()
            self.clock.set_text(dt.strftime('%H:%M'))
            self.last_update = dt
            payload = msg.payload.decode()
            ind = self.indicators.get(msg.topic)
            if ind is not None:
                ind.draw(payload)
        except:
            logger.exception('on message error')

    def on_destroy(self, win):
        self.mqttc.loop_stop()
        Gtk.main_quit()


window = AppWindow()
window.show_all()
Gtk.main()
