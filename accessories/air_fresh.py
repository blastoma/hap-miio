import miio
import math
import logging

from threading import Timer

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SWITCH

logger = logging.getLogger(__name__)

RETRY_INTERVAL = 15

SORTED_MODE_MAP = ((100, miio.airfresh.OperationMode.Strong),
                   (90, miio.airfresh.OperationMode.Middle),
                   (70, miio.airfresh.OperationMode.Low),
                   (50, miio.airfresh.OperationMode.Silent),
                   (30, miio.airfresh.OperationMode.Interval),
                   (10, miio.airfresh.OperationMode.Auto),
                   (0, None))

SORTED_POS_MAP = ((99, 100), (80, 90), (60, 70), (40, 50), (20, 30), (1, 10), (0, 0))


def get_position(m):
    switcher = {
        miio.airfresh.OperationMode.Strong: 100,
        miio.airfresh.OperationMode.Middle: 90,
        miio.airfresh.OperationMode.Low: 70,
        miio.airfresh.OperationMode.Silent: 50,
        miio.airfresh.OperationMode.Interval: 30,
        miio.airfresh.OperationMode.Auto: 10,
        None: 0
    }
    return switcher.get(m, "Invalid Mode")


def get_classification(val, smap):
    assert val >= 0
    return next(state for threshold, state in smap
                if threshold <= val)


class AirFresh(Accessory):

    category = CATEGORY_SWITCH

    def __init__(self, *args, ip, token, **kwargs):
        super().__init__(*args, **kwargs)

        self.ip = ip
        self.token = token

        self.conn = None

        self.mode = None
        self.power = None
        self.pos = None

        self.set_mode_delay = None

        serv_fan = self.add_preload_service('Fan', [
            'RotationSpeed'
        ])

        self.rotation_speed = serv_fan.configure_char('RotationSpeed', setter_callback=self.set_rotation_speed)
        self.on = serv_fan.configure_char('On', setter_callback=self.set_on)

    def set_on(self, value):
        logger.debug('set_on(%s)', value)

        if self.conn is None:
            return

        power = (value == 1)

        if power != self.power:
            self.power = power

            if self.power:
                self.conn.on()
                logger.debug('set_on: self.conn.on()')
            else:
                self.conn.off()
                logger.debug('set_on: self.conn.off()')

    def set_mode(self, mode):
        logger.debug('set_mode(%s)', mode)

        if self.mode != mode:
            self.mode = mode
            self.conn.set_mode(self.mode)
            logger.debug('set_rotation_speed: self.conn.set_mode(%s)', self.mode)

    def set_rotation_speed(self, value):
        logger.debug('set_rotation_speed(%s)', value)

        if self.conn is None:
            return

        if value != self.pos:
            self.pos = get_classification(value, SORTED_POS_MAP)

            self.rotation_speed.set_value(self.pos)
            logger.debug('set_rotation_speed: self.rotation_speed.set_value(%s)', self.pos)

            mode = get_classification(self.pos, SORTED_MODE_MAP)

            if (self.set_mode_delay is not None):
                self.set_mode_delay.cancel()

            self.set_mode_delay = Timer(1.0, self.set_mode, (mode,))
            self.set_mode_delay.start()

    def add_info_service(self):
        info_service = self.driver.loader.get_service('AccessoryInformation')
        info_service.configure_char('Name', value='Air Fresh')
        info_service.configure_char('SerialNumber', value='zhimi.airfresh.va2')
        info_service.configure_char('Model', value='Xiaomi Zhimi Air Fresh')
        info_service.configure_char('Manufacturer', value='Nikolay Borisov')
        self.add_service(info_service)

    @Accessory.run_at_interval(RETRY_INTERVAL)
    async def run(self):
        try:
            if self.conn is None:
                logger.debug("try conn monitor...")
                self.conn = miio.airfresh.AirFresh(ip=self.ip, token=self.token)

            st = self.conn.status()

            power = (st.power == 'on')
            pos = get_position(st.mode)

            if (power != self.power):
                self.power = power
                self.on.set_value(power)
                logger.debug('self.on.set_value(%s)', power)

            if (self.pos != pos):
                self.pos = pos
                self.rotation_speed.set_value(self.pos)
                logger.debug('self.rotation_speed.set_value(%s)', self.pos)

            self.mode = st.mode

            logger.debug(st)

        except Exception as ex:
            logger.error(ex)
