import os
import mip
import urequests
import errno
import micropython
import hashlib
import binascii

try:
    import tarfile
except ImportError:
    mip.install("tarfile")
    import tarfile

import gc

# gc.enable()
print("mem_alloc", gc.mem_alloc())
print("mem_free", gc.mem_free())
# gc.collect()
# gc.disable()

micropython.alloc_emergency_exception_buf(100)

import utils_wlan

class DirCache:
    def __init__(self):
        # List all directories
        # See: https://docs.micropython.org/en/latest/library/os.html#module-os
        self._dirs = [i[0] for i in os.ilistdir() if i[1] == 0x4000]

    def makedir_for_file(self, filename: str) -> None:
        """
        If the filename is in a directory,
        creates that directory if it not exists.
        """
        dirname = filename.rpartition("/")[0]
        if dirname == "":
            return
        if dirname in self._dirs:
            return
        print(f"Create directory {dirname}")
        os.mkdir(dirname)
        self._dirs.append(dirname)



wlan = utils_wlan.WLAN()
# Make sure, the connection before the reboot is dropped.
# wlan.power_off()
wlan.connect()
print("Ready")

URL_APP = "https://hmaerki.github.io/experiment_micropython_mip4/app_a"
response = urequests.get(URL_APP + "/latest/main")
assert response.status_code == 200
with open("config_latest_package.py", "w") as f:
    f.write(response.text)
print(">", response.text, "<")
print("mem_alloc", gc.mem_alloc())
print("mem_free", gc.mem_free())

import config_latest_package
url = URL_APP + config_latest_package.dict_tars["src"]
response = urequests.get(URL_APP + url, stream=True)
assert response.status_code == 200

def save(response, f, chunk_size=2048):
    # https://github.com/SpotlightKid/mrequests/
    size = 0
    hash = hashlib.sha256()

    while True:
        chunk = response.raw.read(chunk_size)
        if not chunk:
            break
        size += len(chunk)
        hash.update(chunk)
        f.write(chunk)

    response.raw.close()
    print("size", size)
    print("sha256", binascii.hexlify(hash.digest()))


with open(sha, "wb") as f:
    save(response, f)


def makedirs(filename: str):
    """
    If the filename is in a directory,
    creates that directory if it not exists.
    Recurses if required.
    """
    dirname = filename.rpartition("/")[0]
    if dirname == "":
        # Top directory
        return
    try:
        os.mkdir(dirname)
    except OSError as ex:
        if ex.errno == errno.EEXIST:
            return
        if ex.errno == errno.ENOENT:
            # The top directory is missing
            makedirs(dirname)
            makedirs(filename)
        assert False, ex


t = tarfile.TarFile(sha)
dircache = DirCache()
for i in t:
    print(i.name)
    if i.type == tarfile.DIRTYPE:
        os.mkdir(i.name)
    else:
        dircache.makedir_for_file(i.name)
        f = t.extractfile(i)
        with open(i.name, "wb") as of:
            of.write(f.read())
