import mip
import urequests
import micropython
import config_secrets

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
print("Connected to WLAN")


def new_version_available(tar_version="src"):
    """
    Return download url if new package is available
    """
    response = urequests.get(config_secrets.URL_APP + config_secrets.BRANCH)
    assert response.status_code == 200
    with open("config_latest_package.py", "w") as f:
        f.write(response.text)

    import config_latest_package

    dict_tar = config_latest_package.DICT_TARS[tar_version]
    try:
        import config_package_manifest
    except ImportError:
        print("New download: Failed to 'import config_package_manifest'")
        return dict_tar
    if config_latest_package.COMMIT_SHA == config_package_manifest.COMMIT_SHA:
        print("No new download!")
        return None

    print(f"New download: {dict_tar} {config_latest_package.COMMIT_PRETTY}")
    return dict_tar


dict_tar = new_version_available()

if dict_tar is not None:
    import utils_download_package
    utils_download_package.download_new_version(dict_tar)
