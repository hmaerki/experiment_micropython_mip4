import os
import mip
import os
import urequests
import micropython

try:
    import tarfile
except ImportError:
    mip.install("tarfile")
    import tarfile

micropython.alloc_emergency_exception_buf(100)

import utils_wlan


wlan = utils_wlan.WLAN()
# Make sure, the connection before the reboot is dropped.
# wlan.power_off()
wlan.connect()
print("Ready")

URL_APP = "https://hmaerki.github.io/experiment_micropython_mip4/app_a"
response = urequests.get(URL_APP + "/latest/main")
print(dir(response))
assert response.status_code == 200
sha = response.text
print(f"{sha=}")

response = urequests.get(URL_APP + "/src/" + sha)
assert response.status_code == 200
with open(sha, "wb") as f:
    f.write(response.content)

t = tarfile.TarFile(sha)
for i in t:
    print(i.name)
    if i.type == tarfile.DIRTYPE:
        os.mkdir(i.name)
    else:
        f = t.extractfile(i)
        with open(i.name, "wb") as of:
            of.write(f.read())
