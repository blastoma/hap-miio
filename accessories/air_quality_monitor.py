import miio
import math
import logging

from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR

logger = logging.getLogger(__name__)

UPDATE_INTERVAL = 5

SORTED_TVOC_QUALITY_MAP = ((2000, 5), (660, 4), (220, 3), (65, 2), (0, 1))
SORTED_PM25_QUALITY_MAP = ((100, 5), (55, 4), (35, 3), (12, 2), (0, 1))
SORTED_CO2_QUALITY_MAP = ((1250, 5), (1000, 4), (750, 3), (500, 2), (0, 1))


def get_quality_classification(val, consts):
    assert val >= 0
    return next(state for threshold, state in consts
                if threshold <= val)


class AirQualityMonitor(Accessory):

    category = CATEGORY_SENSOR

    """
    Threshold-to-state tuples. These show the state for which the threshold is
    lower boundary. Uses something like Air Quality Index (AQI).
    The UI shows:
        1 - Excellent
        2 - Good
        3 - Fair
        4 - Inferior
        5 - Poor
    """

    def __init__(self, *args, ip, token, **kwargs):
        super().__init__(*args, **kwargs)

        self.ip = ip
        self.token = token

        self.conn = None

        serv_quality = self.add_preload_service('AirQualitySensor', [
            'AirQuality',
            'StatusActive',
            'PM2.5Density',
            'VOCDensity',
            'CarbonDioxideLevel'
        ])
        serv_temperature = self.add_preload_service('TemperatureSensor')
        serv_humidity = self.add_preload_service('HumiditySensor')
        serv_co2 = self.add_preload_service('CarbonDioxideSensor', [
            'CarbonDioxideLevel'
        ])
        serv_battery = self.add_preload_service('BatteryService')

        self.active = serv_quality.configure_char('StatusActive')
        self.quality = serv_quality.configure_char('AirQuality')
        self.pm25 = serv_quality.configure_char('PM2.5Density')
        self.co2 = serv_quality.configure_char('CarbonDioxideLevel')
        self.voc = serv_quality.configure_char('VOCDensity')

        self.temperature = serv_temperature.configure_char('CurrentTemperature')

        self.humidity = serv_humidity.configure_char('CurrentRelativeHumidity')

        self.co2_detected = serv_co2.configure_char('CarbonDioxideDetected')
        self.co2_level = serv_co2.configure_char('CarbonDioxideLevel')

        self.battery_level = serv_battery.configure_char('BatteryLevel')
        self.charging_state = serv_battery.configure_char('ChargingState')
        self.low_battery = serv_battery.configure_char('StatusLowBattery')

    def add_info_service(self):
        info_service = self.driver.loader.get_service('AccessoryInformation')
        info_service.configure_char('Name', value='Air Quality')
        info_service.configure_char('SerialNumber', value='cgllc.airmonitor.s1')
        info_service.configure_char('Model', value='Xiaomi Mijia ClearGrass (Qingping) Air Quality Monitor')
        info_service.configure_char('Manufacturer', value='Nikolay Borisov')
        self.add_service(info_service)

    @Accessory.run_at_interval(UPDATE_INTERVAL)
    async def run(self):
        try:
            if self.conn is None:
                logger.debug("try conn monitor...")
                self.conn = miio.airqualitymonitor.AirQualityMonitor(ip=self.ip, token=self.token, model='cgllc.airmonitor.s1')

            st = self.conn.status()
            logger.debug(st)

            quality = math.ceil((get_quality_classification(st.tvoc, SORTED_TVOC_QUALITY_MAP) +
                                 get_quality_classification(st.pm25, SORTED_PM25_QUALITY_MAP) +
                                 get_quality_classification(st.co2, SORTED_CO2_QUALITY_MAP)
                                 ) / 3)

            st.quality = quality
            st.pm25round = round(st.pm25)
            st.low_battery = st.battery < 20
            st.co2_detected = st.co2 > 800

            self.quality.set_value(st.quality)
            self.pm25.set_value(st.pm25round)
            self.co2.set_value(st.co2)
            self.voc.set_value(st.tvoc)
            self.temperature.set_value(st.temperature)
            self.humidity.set_value(st.humidity)
            self.co2_detected.set_value(st.co2_detected)
            self.co2_level.set_value(st.co2)

            self.charging_state.set_value(st.battery == 100)
            self.battery_level.set_value(st.battery)
            self.low_battery.set_value(st.low_battery)
            self.active.set_value(True)

        except Exception as ex:
            logger.error(ex)
            self.active.set_value(False)
