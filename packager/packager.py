import argparse
import pathlib
import tempfile
import subprocess
import shutil
import io
import tarfile
from typing import List

import git
import mpy_cross_v6_1

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
DIRECTORY_REPO = DIRECTORY_OF_THIS_FILE.parent
DIRECTORY_APP_A = DIRECTORY_REPO / "app_a"
DIRECTORY_APP_B = DIRECTORY_REPO / "app_b"
DIRECTORY_WEB_DOWNOADS = DIRECTORY_REPO / "web_downloads"
assert DIRECTORY_APP_A.is_dir()
assert DIRECTORY_APP_B.is_dir()

TAR_SUFFIX = ".tar"


class IndexHtml:
    def __init__(self, app: pathlib.Path, verbose: bool):
        assert isinstance(app, pathlib.Path)
        assert isinstance(verbose, bool)

        self._app = DIRECTORY_WEB_DOWNOADS / app.name
        self._verbose = verbose
        self._app.mkdir(parents=True, exist_ok=True)
        self._index_html = self._app / "index.html"
        self.html = self._index_html.open("w")
        self.html.write(f"<h1>Micropython index for '{app.name}'</h1>\n")

    # def package(self, filename_json: pathlib.Path) -> None:
    #     link = filename_json.relative_to(DIRECTORY_MIP)
    #     self.html.write(f'<h2>Package file</h2>\n')
    #     self.html.write(f'<p><a href="{link}">{link}</a></p>\n')
    #     self.html.write(f"<pre>{filename_json.read_text()}</pre>\n")

    # def write(self)-> None:
    #     (DIRECTORY_MIP /"index.html").write_text(self.html.getvalue())

    def add(self, branch: git.Head) -> None:
        latest = self._app / "latest" / branch.name
        latest.parent.mkdir(parents=True, exist_ok=True)
        latest.write_text(branch.commit.hexsha + TAR_SUFFIX)


class TarSrc:
    def __init__(
        self,
        branch: git.Head,
        app: pathlib.Path,
        globs: List[str],
        verbose: bool,
    ):
        assert isinstance(branch, git.Head)
        assert isinstance(app, pathlib.Path)
        assert isinstance(globs, list)
        assert isinstance(verbose, bool)

        self._verbose = verbose

        tar_filename = (
            DIRECTORY_WEB_DOWNOADS
            / app.name
            / self.version
            / (branch.commit.hexsha + TAR_SUFFIX)
        )

        tar_filename.parent.mkdir(parents=True, exist_ok=True)
        with tar_filename.open("wb") as f:
            with tarfile.open(name="app.tar", mode="w", fileobj=f) as tar:
                for glob in globs:
                    for file in app.rglob(glob):
                        name = str(file.with_suffix(self.py_suffix).relative_to(app))
                        if verbose:
                            print(f"    TarSrc: {name=}")
                        tarinfo = tarfile.TarInfo(name=name)
                        tar.addfile(tarinfo, self._get_file(file))

    def _get_file(self, file: pathlib.Path) -> io.BytesIO:
        assert isinstance(file, pathlib.Path)
        return file.open("rb")

    @property
    def version(self) -> str:
        return "src"

    @property
    def py_suffix(self) -> str:
        return ".py"


class TarMpyCross(TarSrc):
    @property
    def version(self) -> str:
        return "mpy_version/6.1"

    @property
    def py_suffix(self) -> str:
        return ".mpy"

    def _get_file(self, file: pathlib.Path) -> io.BytesIO:
        assert isinstance(file, pathlib.Path)
        # mpy_cross_v6_1.mpy_cross_compile(
        #     filename=file,
        #     file_contents=file.read_text(),
        #     optimization_level=3,
        #     arch=mpy_cross_v6_1.Arch.ARMV6M,
        # )
        with tempfile.NamedTemporaryFile() as tmp_file:
            args = [mpy_cross_v6_1.MPY_CROSS_PATH, "-o", tmp_file.name, str(file)]
            proc = subprocess.run(args, capture_output=True)
            proc.check_returncode()
            if self._verbose:
                print(f"  mpy-cross returned: {proc.stdout.decode().strip()}")
            return io.BytesIO(pathlib.Path(tmp_file.name).read_bytes())


def main(apps: List[str], globs: List[str], verbose: bool) -> None:
    assert isinstance(apps, list)
    assert isinstance(globs, list)
    assert isinstance(verbose, bool)

    shutil.rmtree(DIRECTORY_WEB_DOWNOADS, ignore_errors=True)
    DIRECTORY_WEB_DOWNOADS.mkdir()
    repo = git.Repo(DIRECTORY_REPO)
    assert not repo.bare
    (DIRECTORY_WEB_DOWNOADS/"index.html").write_text("<h1>Downloads</h1>")
    for app in [pathlib.Path(a) for a in apps]:
        if verbose:
            print(f"app: {app.name}")

        for branch in repo.branches:
            index_app = IndexHtml(app=app, verbose=verbose)
            if verbose:
                print(f"  branch={branch.name} sha={branch.commit.hexsha}")
            index_app.add(branch=branch)

            globs = ["*.py", "*.txt"]
            for cls_tar in (TarSrc, TarMpyCross):
                cls_tar(branch=branch, app=app, globs=globs, verbose=verbose)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        type=bool,
        default=False,
    )
    parser.add_argument(
        "--glob",
        action="append",
        help="File suffix. For example '*.py'.",
    )
    parser.add_argument(
        "app",
        nargs="+",
        help="The application directory",
    )
    args = parser.parse_args()

    # print(f"{args.globs=}")
    # print(f"{args.app=}")

    main(
        apps=args.app,
        globs=args.glob,
        verbose=args.verbose,
    )
