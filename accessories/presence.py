import os
import logging

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR

logger = logging.getLogger(__name__)

UPDATE_INTERVAL = 30


def ping(hostname):
    response = os.system("ping -c 1 " + hostname)

    if response == 0:
        logger.debug('%s is up!', hostname)
    else:
        logger.debug('%s is down!', hostname)

    return response == 0


class Presence(Accessory):

    category = CATEGORY_SENSOR

    def __init__(self, *args, hostname, **kwargs):
        super().__init__(*args, **kwargs)

        self.hostname = hostname
        self.retries = 0

        serv_sensor = self.add_preload_service('OccupancySensor')
        self.detected = serv_sensor.configure_char('OccupancyDetected')

    def add_info_service(self):
        info_service = self.driver.loader.get_service('AccessoryInformation')
        info_service.configure_char('Name', value='Presence')
        info_service.configure_char('SerialNumber', value='presence.detector')
        info_service.configure_char('Model', value='IP Presence Detector')
        info_service.configure_char('Manufacturer', value='Nikolay Borisov')
        self.add_service(info_service)

    @Accessory.run_at_interval(UPDATE_INTERVAL)
    async def run(self):
        prs = ping(self.hostname)
        if prs:
            self.detected.set_value(True)
            self.retries = 0
        else:
            self.retries += 1
            if self.retries > 9:
                self.detected.set_value(False)
