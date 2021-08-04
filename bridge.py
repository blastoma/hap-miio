#!/usr/bin/python3

import logging
import signal

import pyhap.util as util
from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver

from accessories.air_quality_monitor import AirQualityMonitor
from accessories.vacuum import Vacuum
from accessories.air_fresh import AirFresh
from accessories.presence import Presence
from accessories.dummy_switch import DummySwitch


logging.basicConfig(level=logging.DEBUG)


driver = AccessoryDriver(port=54321, pincode=bytearray(b'111-11-111'), mac=util.generate_mac())
bridge = Bridge(driver, 'Bridge')


air_quality = AirQualityMonitor(driver, 'Air Monitor', ip='192.168.1.1', token='XXX')
bridge.add_accessory(air_quality)

air_fresh = AirFresh(driver, 'Air Fresh', ip='192.168.1.71', token='XXX')
bridge.add_accessory(air_fresh)

driver.add_accessory(bridge)

signal.signal(signal.SIGTERM, driver.signal_handler)

driver.start()

print('Bridge Ready')
