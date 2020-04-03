import miio
import math
import logging

from threading import Timer

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_FAN

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

UPDATE_INTERVAL = 30

SORTED_PM25_QUALITY_MAP = ((100, 5), (55, 4), (35, 3), (12, 2), (0, 1))
SORTED_CO2_QUALITY_MAP = ((1250, 5), (1000, 4), (750, 3), (500, 2), (0, 1))


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

    category = CATEGORY_FAN

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

        serv_quality = self.add_preload_service('AirQualitySensor', [
            'AirQuality',
            'StatusActive',
            'PM2.5Density',
            'CarbonDioxideLevel'
        ])
        serv_temperature = self.add_preload_service('TemperatureSensor', [
            'StatusActive'
        ])
        serv_humidity = self.add_preload_service('HumiditySensor', [
            'StatusActive'
        ])
        serv_co2 = self.add_preload_service('CarbonDioxideSensor', [
            'StatusActive',
            'CarbonDioxideLevel'
        ])

        self.quality_active = serv_quality.configure_char('StatusActive')
        self.quality = serv_quality.configure_char('AirQuality')
        self.pm25 = serv_quality.configure_char('PM2.5Density')
        self.co2 = serv_quality.configure_char('CarbonDioxideLevel')

        self.temperature_active = serv_temperature.configure_char('StatusActive')
        self.temperature = serv_temperature.configure_char('CurrentTemperature')

        self.humidity_active = serv_humidity.configure_char('StatusActive')
        self.humidity = serv_humidity.configure_char('CurrentRelativeHumidity')

        self.co2_active = serv_co2.configure_char('StatusActive')
        self.co2_detected = serv_co2.configure_char('CarbonDioxideDetected')
        self.co2_level = serv_co2.configure_char('CarbonDioxideLevel')

        self.rotation_speed = serv_fan.configure_char('RotationSpeed', setter_callback=self.set_rotation_speed)
        self.on = serv_fan.configure_char('On', setter_callback=self.set_on)

    def set_active(self, active):
        self.quality_active.set_value(active)
        self.co2_active.set_value(active)
        self.temperature_active.set_value(active)
        self.humidity_active.set_value(active)

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

    @Accessory.run_at_interval(UPDATE_INTERVAL)
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

            if power:
                quality = math.ceil((
                                    get_classification(st.aqi, SORTED_PM25_QUALITY_MAP) +
                                    get_classification(st.co2, SORTED_CO2_QUALITY_MAP)
                                    ) / 2)

                st.quality = quality
                st.co2_detected = st.co2 > 800

                self.quality.set_value(st.quality)
                self.pm25.set_value(st.aqi)
                self.co2.set_value(st.co2)
                self.temperature.set_value(st.temperature)
                self.humidity.set_value(st.humidity)
                self.co2_detected.set_value(st.co2_detected)
                self.co2_level.set_value(st.co2)

                logger.error(st.humidity)
                logger.error(st.temperature)

                self.set_active(True)
            else:
                self.set_active(False)

        except Exception as ex:
            logger.error(ex)
            self.set_active(False)
