import miio
import logging

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SWITCH

logger = logging.getLogger(__name__)

UPDATE_INTERVAL = 30


class Vacuum(Accessory):

    category = CATEGORY_SWITCH

    def __init__(self, *args, ip, token, **kwargs):
        super().__init__(*args, **kwargs)

        self.ip = ip
        self.token = token

        self.conn = None

        serv_switch = self.add_preload_service('Switch')
        self.char_on = serv_switch.configure_char('On', setter_callback=self.clean)

        serv_battery = self.add_preload_service('BatteryService')
        self.battery_level = serv_battery.configure_char('BatteryLevel')
        self.charging_state = serv_battery.configure_char('ChargingState')
        self.low_battery = serv_battery.configure_char('StatusLowBattery')

        self.st = None

    def clean(self, value):
        if value == 0:
            self.conn.home()
            logger.debug('self.conn.home()')
        else:
            self.conn.resume_or_start()
            logger.debug('self.conn.resume_or_start()')

        self.run()

    def add_info_service(self):
        info_service = self.driver.loader.get_service('AccessoryInformation')
        info_service.configure_char('Name', value='Vacuum')
        info_service.configure_char('SerialNumber', value='rockrobo.vacuum.v1')
        info_service.configure_char('Model', value='Xiaomi Mi Robot Vacuum')
        info_service.configure_char('Manufacturer', value='Nikolay Borisov')
        self.add_service(info_service)

    @Accessory.run_at_interval(UPDATE_INTERVAL)
    async def run(self):
        try:
            if self.conn is None:
                logger.debug("try conn monitor...")
                self.conn = miio.vacuum.Vacuum(ip=self.ip, token=self.token)

            st = self.conn.status()

            logger.debug(st)

            st.low_battery = (st.battery < 20)
            st.charging_state = (st.state == 'Charging')

            self.battery_level.set_value(st.battery)
            self.charging_state.set_value(st.charging_state)
            self.low_battery.set_value(st.low_battery)

            self.char_on.set_value(int(st.is_on))

            self.st = st

            logger.debug(st)

        except Exception as ex:
            logger.error(ex)
