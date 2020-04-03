import logging

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SWITCH

logger = logging.getLogger(__name__)

UPDATE_INTERVAL = 30


class DummySwitch(Accessory):

    category = CATEGORY_SWITCH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serv_switch = self.add_preload_service('Switch')
        self.on = serv_switch.configure_char('On', setter_callback=self.set_on)

    def set_on(self, value):
        logger.debug('set_on(%s)', value)

    def add_info_service(self):
        info_service = self.driver.loader.get_service('AccessoryInformation')
        info_service.configure_char('Name', value='Dummy Switch')
        info_service.configure_char('SerialNumber', value='dummy.switch')
        info_service.configure_char('Manufacturer', value='Nikolay Borisov')
        self.add_service(info_service)

    @Accessory.run_at_interval(UPDATE_INTERVAL)
    async def run(self):
        self.on.set_value(self.on.get_value() == False)
