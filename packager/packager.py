import argparse
import pathlib
import tempfile
import subprocess
import shutil
import io
import tarfile
from typing import Iterator, List

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
    def __init__(self, directory: pathlib.Path, title: str, verbose: bool):
        assert isinstance(directory, pathlib.Path)
        assert isinstance(title, str)
        assert isinstance(verbose, bool)

        self._verbose = verbose
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.html = self.filename.open("w")
        self.set_h1(title=title)

    @property
    def filename(self) -> pathlib.Path:
        return self.directory / "index.html"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.html.close()

    def set_h1(self, title: str) -> None:
        self.html.write(f"<h1>{title}</h1>\n")

    # def package(self, filename_json: pathlib.Path) -> None:
    #     link = filename_json.relative_to(DIRECTORY_MIP)
    #     self.html.write(f'<h2>Package file</h2>\n')
    #     self.html.write(f'<p><a href="{link}">{link}</a></p>\n')
    #     self.html.write(f"<pre>{filename_json.read_text()}</pre>\n")

    # def write(self)-> None:
    #     (DIRECTORY_MIP /"index.html").write_text(self.html.getvalue())

    def set_href(self, link: pathlib.Path, label: str) -> None:
        self.html.write(
            f'<p><a href="{link.relative_to(self.directory)}">{label}</a></p>\n'
        )

    def new_index(self, relative: str, title: str) -> "IndexHtml":
        directory = self.directory / relative
        self.set_href(link=directory, label=title)
        return IndexHtml(directory=directory, title=title, verbose=self._verbose)

    def add_branch(self, head: git.HEAD) -> None:
        if self._verbose:
            print(f"  branch={head.name} sha={head.commit.hexsha}")
        latest = self.directory / "latest" / head.name
        latest.parent.mkdir(parents=True, exist_ok=True)
        latest.write_text(head.commit.hexsha + TAR_SUFFIX)
        self.set_href(link=latest, label=f"Latest on branch {head.name}")


class TarSrc:
    def __init__(
        self,
        head: git.HEAD,
        app: pathlib.Path,
        globs: List[str],
        verbose: bool,
    ):
        assert isinstance(head, git.HEAD)
        assert isinstance(app, pathlib.Path)
        assert isinstance(globs, list)
        assert isinstance(verbose, bool)

        self._verbose = verbose

        tar_filename = (
            DIRECTORY_WEB_DOWNOADS
            / app.name
            / self.version
            / (head.commit.hexsha + TAR_SUFFIX)
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


class Git:
    def __init__(self):
        self._repo = git.Repo(DIRECTORY_REPO)
        assert not self._repo.bare
        self.remote_heads: List[str] = [ref.remote_head for ref in self._iter_refs]

    @property
    def _iter_refs(self) -> Iterator[git.RemoteReference]:
        for ref in self._repo.refs:
            if not isinstance(ref, git.RemoteReference):
                continue
            if ref.remote_head == "HEAD":
                continue
            yield ref

    def _get_ref(self, remote_head: str) -> git.RemoteReference:
        for ref in self._iter_refs:
            if ref.remote_head == remote_head:
                return ref
        raise Exception(f"Not found: remote_head '{remote_head}'")

    def checkout(self, remote_head: str) -> git.HEAD:
        ref = self._get_ref(remote_head=remote_head)
        head = ref.checkout()
        assert isinstance(head,git.HEAD)
        return head


def main(apps: List[str], globs: List[str], verbose: bool) -> None:
    assert isinstance(apps, list)
    assert isinstance(globs, list)
    assert isinstance(verbose, bool)

    shutil.rmtree(DIRECTORY_WEB_DOWNOADS, ignore_errors=True)
    DIRECTORY_WEB_DOWNOADS.mkdir()
    git = Git()

    with IndexHtml(
        directory=DIRECTORY_WEB_DOWNOADS, title="Downloads", verbose=verbose
    ) as index_top:
        for app in [pathlib.Path(a).absolute() for a in apps]:
            if verbose:
                print(f"app: {app.name}")
            with index_top.new_index(
                relative=app.name,
                title=f"Application <b>{app.name}</b>",
            ) as index_app:
                for branch in git.remote_heads:
                    head = git.checkout(remote_head=branch)
                    index_app.add_branch(head=head)

                    globs = ["*.py", "*.txt"]
                    for cls_tar in (TarSrc, TarMpyCross):
                        cls_tar(head=head, app=app, globs=globs, verbose=verbose)


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
