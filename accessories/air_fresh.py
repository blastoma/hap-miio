import miio
import math
import logging

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SWITCH

logger = logging.getLogger(__name__)

UPDATE_INTERVAL = 10

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

        serv_fan = self.add_preload_service('Fan', [
            'RotationSpeed'
        ])

        self.rotation_speed = serv_fan.configure_char('RotationSpeed', setter_callback=self.set_rotation_speed)
        self.on = serv_fan.configure_char('On', setter_callback=self.set_on)

    def set_on(self, value):
        logger.debug('set_on(%s):', value)
        # if self.conn is not None:
        if value:
            self.conn.on()
            logger.debug('self.conn.on()')
        else:
            self.conn.off()
            logger.debug('self.conn.off()')

    def set_rotation_speed(self, value):
        logger.debug('set_rotation_speed(%s):', value)
        pos = get_classification(value, SORTED_POS_MAP)
        mode = get_classification(pos, SORTED_MODE_MAP)

        # if self.conn is not None:
        if mode is None:
            logger.debug('set_rotation_speed > mode is None')
            # self.on.set_value(False)
            # self.conn.off()
        else:
            logger.debug('set_rotation_speed > mode is not None')
            # self.on.set_value(True)
            # self.conn.on()
            self.conn.set_mode(mode)
            logger.debug('self.conn.set_mode(%s)', mode)
            # if self.st.mode != mode:

        self.rotation_speed.set_value(pos)
        logger.debug('self.rotation_speed.set_value(%s)', pos)

    def add_info_service(self):
        info_service = self.driver.loader.get_service('AccessoryInformation')
        info_service.configure_char('Name', value='Air Fresh')
        info_service.configure_char('SerialNumber', value='zhimi.airfresh.va2')
        info_service.configure_char('Model', value='Xiaomi Zhimi Air Fresh')
        info_service.configure_char('Manufacturer', value='Nikolay Borisov')
        self.add_service(info_service)

    # @Accessory.run_at_interval(UPDATE_INTERVAL)
    async def run(self):
        try:
            if self.conn is None:
                logger.debug("try conn monitor...")
                self.conn = miio.airfresh.AirFresh(ip=self.ip, token=self.token)

            st = self.conn.status()

            if st.power == 'off':
                self.on.set_value(False)
                logger.debug('self.on.set_value(False)')
            else:
                self.on.set_value(True)
                logger.debug('self.on.set_value(True)')

            pos = get_position(st.mode)
            self.rotation_speed.set_value(pos)
            logger.debug('self.rotation_speed.set_value(%s)', pos)

            logger.debug(st)

            self.st = st

        except Exception as ex:
            logger.error(ex)
