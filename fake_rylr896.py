# import busio
# import board
import time
import random

try:
    import adafruit_hashlib as hashlib
except:
    import hashlib


class ReceivedMessage(object):

    def __init__(self, address: int = None, payload_length: int = None, actual_data: str = None,
                 received_signal_strength_indicator: int = None,
                 signal_noise_ratio: int = None):
        self.addr = address
        self.pl = payload_length
        self.dat = actual_data
        self.rssi = received_signal_strength_indicator
        self.snr = signal_noise_ratio
        m = hashlib.sha256()
        m.update(address)
        m.update(actual_data)
        self.msg_hash = m.digest()

    def get_dictionary(self) -> dict:
        return {
            "address": int(self.addr),
            "length": int(self.pl),
            "data": self.dat,
            "rssi": int(self.rssi),
            "snr": int(self.snr),
            "time": float(time.time()),
            "hash": self.msg_hash
        }


class RYLR896:
    __debug = None

    def __init__(self, tx=None, rx=None, timeout=.5, debug=False, name=None, repeater=False):
        if name is None:
            self.name = self.__class__.__name__
        else:
            self.name = name
        self.__debug = debug
        assert rx is not None and tx is not None
        self.check = False
        self.timeout = timeout
        self.set_device_timeout()
        if self.test_device():
            self.factory_reset()
            print("{} is factory reset and ready to use".format(self.name))
            self.address = 0
            self.band = 915000000
            self.cpin = "No Password!"
            self.rf_power = 15
            self.mode = 0
            self.network_id = 0
            self.spread_factor = 12
            self.bandwidth = 7
            self.coding_rate = 1
            self.last_sent = None
            self.programmed_preamble = 4
            self.check = True
        else:
            print("Failed to establish communication with {}".format(self.name))
            self.check = False

    def set_device_timeout(self, timeout_to_use: float = .5):
        self.timeout = timeout_to_use

    def __generate_fake_msg(self, n):
        response = ""
        for i in range(n):
            response += chr(random.randint(93, 93 + 26))
        return response

    def read_from_device(self):
        """
        THE TIME MIGHT BE FUCKIN BAD, DEAL WITH IT. we'll add time syncs later.

        :return:
        """

        """returns a dictionary
        {
        "address":int(self.addr),
        "length":int(self.pl),
        "data":self.dat,
        "rssi":int(self.rssi),
        "snr":int(self.snr),
        "time":float(time.time()),
        "hash":self.msg_hash
        }
        """
        msg = self.__generate_fake_msg(random.randint(4, 60))
        address, payload_length, data, rssi, snr = (
        random.randint(1, 65535), len(msg), msg, random.randint(-100, -1), random.randint(20, 70))
        msg = ReceivedMessage(address=address, payload_length=payload_length, actual_data=data,
                              received_signal_strength_indicator=rssi, signal_noise_ratio=snr)
        return msg.get_dictionary()

    def set_address(self, address_to_use: int) -> bool:
        """
        Set the address of the device
        :param (int) address_to_use: 0-65535
        :return: True on success, False on failure
        """
        if address_to_use < 0:
            raise "{} -- Address not allowed".format(self.name)
        if address_to_use > 65535:
            raise "{} ++ Address not allowed".format(self.name)

        self.address = address_to_use

        return True

    def get_address(self) -> int:
        """
        gets address of device.
        :return: int of address
        """
        return self.address

    def test_device(self):
        return True

    def set_band(self, band_to_use: int) -> bool:
        if band_to_use < 862000000:
            raise "Band not allowed"
        if band_to_use > 1020000000:
            raise "Band not allowed"

        self.band = band_to_use
        return True

    def get_band(self) -> int:
        return self.band

    def set_cpin(self, cpin_to_use: str) -> bool:
        try:
            val = int(cpin_to_use, 16)
        except:
            raise "cpin is not hex string"
        if len(cpin_to_use) > 32:
            raise "cpin is too long"

        self.cpin = cpin_to_use
        return True

    def get_cpin(self) -> str:
        return self.cpin

    def set_rf_power_out(self, rf_power_to_use: int) -> bool:
        if rf_power_to_use < 0:
            raise "rf power not allowed"
        if rf_power_to_use > 15:
            raise "rf power not allowed"

        self.rf_power = rf_power_to_use
        return True

    def get_rf_power_out(self) -> int:
        return self.rf_power

    def factory_reset(self):
        return True

    def sw_reset(self):
        return True

    def set_mode(self, mode_to_use: int) -> bool:
        self.mode = mode_to_use
        return True

    def set_network_id(self, network_id_to_use: int) -> bool:
        if 0 <= network_id_to_use <= 16:
            pass
        else:
            raise "Bad network id. Must be 0-16"
        self.network_id = network_id_to_use
        return True

    def get_network_id(self):
        return self.network_id

    def set_rf_parameters(self, sf_to_use: int, bw_to_use: int, cr_to_use: int, pp_to_use: int) -> bool:
        if 7 <= sf_to_use <= 12:
            pass
        else:
            raise "Bad spreadfactor. Must be 7-12"
        if 2 <= bw_to_use <= 9:
            pass
        else:
            raise "Bad bandwidth. Must be 0-9"
        if 1 <= cr_to_use <= 4:
            pass
        else:
            raise "Bad coding rate. Must be 1-4"
        if 4 <= pp_to_use <= 7:
            pass
        else:
            raise "Bad programmed preamble. Must be 4-7"

        self.spread_factor = sf_to_use
        self.bandwidth = bw_to_use
        self.coding_rate = cr_to_use
        self.programmed_preamble = pp_to_use
        return True

    def get_rf_parameters(self):
        return self.spread_factor, self.bandwidth, self.coding_rate, self.programmed_preamble

    def send(self, data: str = None, address: int = 0) -> bool:
        if 0 <= address <= 65535:
            pass
        else:
            raise "{} Bad address".format(self.name)
        if data is None:
            raise "{} Bad data, cannot be none".format(self.name)
        try:
            bytes(data, "utf-8")
        except:
            raise "{} Bad data".format(self.name)

        self.last_sent = "+SEND={},{},{}".format(address, len(data), data)
        chance = random.randint(1, 100)
        if chance < 2:
            return False
        else:
            return True

    def get_last_sent(self):
        return self.last_sent

    def get_firmware_version(self):
        return "+VER=RYLR89C_V1.1.1"

    def get_UID(self):
        return "+UID=164738323135383200100025"
