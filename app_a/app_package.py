import pathlib

name = "app_b"
directory = pathlib.Path(__file__).parent / "micropython"
globs = ["*.py", "*.txt"]

assert directory.exists(), str(directory)
