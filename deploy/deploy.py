"""
https://github.com/micropython/micropython-lib/blob/master/tools/build.py
"""
import io
import json
import os
import shutil
import sys
import hashlib
import pathlib
import subprocess
import tempfile

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
DIRECTORY_REPO = DIRECTORY_OF_THIS_FILE.parent

DIRECTORY_SRC = DIRECTORY_REPO / "src"
assert DIRECTORY_SRC.is_dir()

DIRECTORY_MIP = DIRECTORY_REPO / "mip"
assert DIRECTORY_MIP.is_dir()
DIRECTORY_PACKAGES = DIRECTORY_MIP / "package"

MYPY_VERSION = 6
PACKAGE_NAME = "dryer2023"

DIRECTORY_PACKAGE = DIRECTORY_PACKAGES / str(MYPY_VERSION) / PACKAGE_NAME
DIRECTORY_FILE = DIRECTORY_MIP / "file"

BRANCH = "main"
HASH_PREFIX_LEN = 12


# Returns the sha256 of the specified file object.
def _get_file_hash(mpy_code: bytes):
    hs256 = hashlib.sha256()
    hs256.update(mpy_code)
    return hs256.hexdigest()


# Copy src to "file"/{short_hash[0:2]}/{short_hash}.
def _write_hashed_file(
    package_name: str,
    mpy_code: bytes,
    py_code: str,
    filename_py: str,
    directory_file: pathlib.Path,
    hash_prefix_len: int,
):
    # Generate the full sha256 and the hash prefix to use as the output path.
    file_hash = _get_file_hash(mpy_code)
    short_file_hash = file_hash[:hash_prefix_len]
    # Group files into subdirectories using the first two bytes of the hash prefix.
    output_file = os.path.join(short_file_hash[:2], short_file_hash)
    output_file_path = directory_file / output_file

    # Hack: Just ignore hash conflicts
    output_file_path.unlink(missing_ok=True)

    if output_file_path.is_file():
        # If the file exists (e.g. from a previous run of this script), then ensure
        # that it's actually the same file.
        if not _identical_files(mpy_code.name, output_file_path):
            print(
                error_color("Hash collision processing:"),
                package_name,
                file=sys.stderr,
            )
            print("  File:        ", filename_py, file=sys.stderr)
            print("  Short hash:  ", short_file_hash, file=sys.stderr)
            print("  Full hash:   ", file_hash, file=sys.stderr)
            with open(output_file_path, "rb") as f:
                print("  Target hash: ", _get_file_hash(f), file=sys.stderr)
            print("Try increasing --hash-prefix (currently {})".format(hash_prefix_len))
            sys.exit(1)
    else:
        # Create new file.
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file_path.write_bytes(mpy_code)
        output_file_path.with_suffix(".py").write_text(py_code)

    return short_file_hash

class IndexHtml:
    def __init__(self):
        self.html = io.StringIO()
        self.html.write("<h1>Micropython MIP index.</h1>\n")
        self.html.write("<h2>Installation</h2>\n")
        self.html.write("""<pre>import mip
mip.install("{PACKAGE_NAME}", version="main", index="https://hmaerki.github.io/experiment_micropython_mip")\n
""")

    def package(self, filename_json: pathlib.Path) -> None:
        link = filename_json.relative_to(DIRECTORY_MIP)
        self.html.write(f'<h2>Package file</h2>\n')
        self.html.write(f'<p><a href="{link}">{link}</a></p>\n')
        self.html.write(f"<pre>{filename_json.read_text()}</pre>\n")

    def write(self)-> None:
        (DIRECTORY_MIP /"index.html").write_text(self.html.getvalue())

def main():
    package_json = {
        "hashes": [],
        "deps": [
            [
                "https://micropython.org/pi/v2/package/6/umqtt.simple/latest.json",
                "dummy",
            ]
        ],
        "version": "0.1",
    }

    shutil.rmtree(DIRECTORY_PACKAGE, ignore_errors=True)
    DIRECTORY_PACKAGE.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(DIRECTORY_FILE, ignore_errors=True)
    DIRECTORY_FILE.mkdir(parents=True, exist_ok=True)

    for filename_py in (DIRECTORY_SRC / PACKAGE_NAME).glob("*.py"):
        with tempfile.NamedTemporaryFile(
            mode="rb", suffix=".mpy", delete=True
        ) as mpy_tempfile:
            proc = subprocess.run(
                [
                    "python",
                    "-m",
                    "mpy_cross",
                    "-o",
                    mpy_tempfile.name,
                    str(filename_py),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise Exception(
                    f"{proc.args}: returned {proc.returncode}:\n {proc.stdout} \n---\n {proc.stderr}"
                )

            short_mpy_hash = _write_hashed_file(
                PACKAGE_NAME,
                mpy_tempfile.read(),
                filename_py.read_text(),
                filename_py=filename_py,
                directory_file=DIRECTORY_FILE,
                hash_prefix_len=HASH_PREFIX_LEN,
            )

            # Add the file to the package json.
            filename_mpy = filename_py.with_suffix(".mpy")
            package_json["hashes"].append((f"{PACKAGE_NAME}/{filename_mpy.name}", short_mpy_hash))

    filename_json = DIRECTORY_PACKAGE / f"{BRANCH}.json"
    with filename_json.open("w") as f:
        json.dump(package_json, f, indent=4, sort_keys=True)

    index = IndexHtml()
    index.package(filename_json=filename_json)
    index.write()

if __name__ == "__main__":
    main()
    