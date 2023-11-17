import pathlib

name = "app_b"
directory = pathlib.Path(__file__).parent
globs = ["*.py", "*.txt"]

assert directory.exists(), str(directory)
