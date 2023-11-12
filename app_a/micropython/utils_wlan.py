import time
import rp2
import network

import config_secrets

# https://github.com/micropython/micropython/issues/11977
country = const("CH")
rp2.country(country)
network.country(country)


WLAN_CONNECT_TIME_OUT_MS = const(10000)


class WLAN:
    def __init__(self):
        self._wdt_feed = lambda: False
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.config(pm=network.WLAN.PM_PERFORMANCE)
        self.connection_counter = 0
        # time.sleep(1.0)
        # print(f"DEBUG: reset 2: {self._wlan.isconnected()}, {self._wlan.status()}")

    def register_wdt_feed_cb(self, wdt_feed_cb):
        """
        When using the wdt, using this callbac, this WLAN class
        will call the watchdog whenever possible.
        """
        self._wdt_feed = wdt_feed_cb

    def power_on(self) -> None:
        """
        Power of the WLAN interface
        """
        # print(f"DEBUG: interface_start 1: {self.status_text}")
        self._wlan.active(True)
        # print(f"DEBUG: interface_start 2: {self.status_text}")

    def power_off(self) -> None:
        """
        Power off the WLAN
        https://github.com/orgs/micropython/discussions/10889

        Sometimes a WLAN connection is dangeling in a unwanted state.
        `power_off()` normally recovers and allows us to create a brand
        new connection.
        """
        # print(f"DEBUG: interface_stop 1: {self.status_text}")
        self._wlan.disconnect()
        # print(f"DEBUG: interface_stop 2: {self.status_text}")
        self._wlan.active(False)
        # print(f"DEBUG: interface_stop 3: {self.status_text}")
        self._wlan.deinit()
        # print(f"DEBUG: interface_stop 4: {self.status_text}")

    def get_status_name(self, status: int):
        """
        Returns the text related to `_wlan.status()`
        """
        for k, v in network.__dict__.items():
            if k.startswith("STAT_"):
                if v == status:
                    return k
        return "??"

    @property
    def status_text(self):
        """
        Returns a summary text for the wlan interface
        """
        status = self._wlan.status()
        return f"isconnected: {self._wlan.isconnected()}, status: {status}({self.get_status_name(status)}), ip_address: {self.ip_address}"

    @property
    def ip_address(self):
        return self._wlan.ifconfig()[0]

    def _find_ssid(self):
        """
        returns (ssid, password)
        or (None, None)
        """
        # Scan the wlan
        self._wdt_feed()
        set_ssids = {l[0] for l in self._wlan.scan()}

        if len(set_ssids) == 0:
            print("WARNING: WLANs.scan() returned empty list!")
            return (None, None)

        for ssid, password in config_secrets.SSID_CREDENTIALS:
            assert isinstance(ssid, bytes), ssid
            assert isinstance(password, str), password
            if ssid in set_ssids:
                print(f"DEBUG: selected network: {ssid}")
                return (ssid, password)

        print("WARNING: WLANs.scan(): No matching network seen!")
        return (None, None)

    @property
    def ip_address(self):
        return self._wlan.ifconfig()[0]

    @property
    def got_ip_address(self) -> bool:
        """
        Return True if we have a ip address assigned.
        IMPORTANT: Even we do not generated ip traffic, `got_ip_address` will return False
        in about 5s after the AP dissapeared.
        So this is a good indication if the WLAN connection is lost.
        """
        if not self._wlan.isconnected():
            return False
        return self.ip_address != "0.0.0.0"

    def connect(self) -> bool:
        """
        Return True if connection could be established
        """
        try:
            if self.got_ip_address:
                return True
            print(f"DEBUG: connecting WLAN ...")
            self._wdt_feed()
            self.power_off()
            time.sleep(1)
            self.power_on()
            ssid, password = self._find_ssid()
            if ssid is None:
                # print("WARNING: No known SSID!")
                return False
            print(f"DEBUG: connecting WLAN '{ssid:s}' ...")
            self._wdt_feed()
            self._wlan.connect(ssid, password)
            start_ms = time.ticks_ms()
            while True:
                self._wdt_feed()
                duration_ms = time.ticks_diff(time.ticks_ms(), start_ms)
                if self.got_ip_address:
                    break
                if duration_ms > WLAN_CONNECT_TIME_OUT_MS:
                    print(
                        f"WARNING: Timeout of {duration_ms}ms while waiting for connection!"
                    )
                    return False
                time.sleep(1)
            print(
                f"DEBUG: Connected within {duration_ms}ms to {ssid} and ip {self.ip_address}"
            )
            self.connection_counter += 1
            return True
        except OSError as e:
            print(f"ERROR: wlan.connect() failed: {e}")
            return False
