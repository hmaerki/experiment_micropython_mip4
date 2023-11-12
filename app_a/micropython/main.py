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
    url = config_secrets.URL_APP + config_secrets.BRANCH
    response = urequests.get(url)
    assert response.status_code == 200, (response.status_code, url)
    latest_package = response.json()

    # print("response.text", response.text)
    # print("latest_package", latest_package)

    dict_tar = latest_package["dict_tars"][tar_version]

    try:
        import config_package_manifest
    except ImportError:
        print("New download: Failed to 'import config_package_manifest'")
        return dict_tar
    # print("dict_tar", dict_tar)
    if latest_package["commit_sha"] == config_package_manifest.COMMIT_SHA:
        print("No new download!")
        return None

    print(f"New download: {latest_package['commit_pretty']}")
    return dict_tar


while True:
    dict_tar = new_version_available()

    if dict_tar is not None:
        import utils_download_package

        utils_download_package.download_new_version(dict_tar)

    print("B")
