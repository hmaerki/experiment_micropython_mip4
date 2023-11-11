import pathlib
import shutil
import io
import tarfile
from typing import List

import git

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
DIRECTORY_REPO = DIRECTORY_OF_THIS_FILE.parent
DIRECTORY_APP_A = DIRECTORY_REPO / "app_a"
DIRECTORY_APP_B = DIRECTORY_REPO / "app_b"
DIRECTORY_WEB_DOWNOADS = DIRECTORY_REPO / "web_downloads"
assert DIRECTORY_APP_A.is_dir()
assert DIRECTORY_APP_B.is_dir()


class IndexHtml:
    def __init__(self, directory_app: pathlib.Path):
        assert isinstance(directory_app, pathlib.Path)
        self._directory_app = directory_app
        self._directory_app.mkdir(parents=True, exist_ok=True)
        self._index_html = self._directory_app / "index.html"
        self.html = self._index_html.open("w")
        self.html.write(f"<h1>Micropython index for '{directory_app.name}'</h1>\n")

    # def package(self, filename_json: pathlib.Path) -> None:
    #     link = filename_json.relative_to(DIRECTORY_MIP)
    #     self.html.write(f'<h2>Package file</h2>\n')
    #     self.html.write(f'<p><a href="{link}">{link}</a></p>\n')
    #     self.html.write(f"<pre>{filename_json.read_text()}</pre>\n")

    # def write(self)-> None:
    #     (DIRECTORY_MIP /"index.html").write_text(self.html.getvalue())

    def add(self, branch: git.Head) -> None:
        latest = self._directory_app / "latest" / branch.name
        latest.parent.mkdir(parents=True, exist_ok=True)
        latest.write_text(branch.commit.hexsha)

    def add_package(self, branch: git.Head, version: str, data: bytes) -> None:
        filename = self._directory_app / version / branch.commit.hexsha
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_bytes(data)


class TarSrc:
    def __init__(
        self, directory_app: pathlib.Path, globs: List[str] = ["*.py", "*.txt"]
    ):
        assert isinstance(directory_app, pathlib.Path)
        self._f = io.BytesIO()
        self._tar = tarfile.open(name="xy.tar", mode="w", fileobj=self._f)
        for glob in globs:
            for f in directory_app.rglob(glob):
                name = f.relative_to(directory_app).name
                tarinfo = tarfile.TarInfo(name=name)
                self._tar.addfile(tarinfo, self._get_file(f))

    def _get_file(self, file: pathlib.Path) -> io.BytesIO:
        return io.BytesIO(b"123")

    @property
    def data(self) -> bytes:
        return self._f.getvalue()


def main():
    shutil.rmtree(DIRECTORY_WEB_DOWNOADS, ignore_errors=True)
    repo = git.Repo(DIRECTORY_REPO)
    assert not repo.bare
    # index_top = IndexHtml(DIRECTORY_WEB_DOWNOADS)
    for app in (DIRECTORY_APP_A, DIRECTORY_APP_B):
        for branch in repo.branches:
            index_app = IndexHtml(DIRECTORY_WEB_DOWNOADS / app.name)
            print(f"{branch.name=} {branch.commit.hexsha=}")
            index_app.add(branch=branch)
            tar = TarSrc(directory_app=app, globs=["*.py", "*.txt"])
            index_app.add_package(branch=branch, version="src", data=tar.data)


if __name__ == "__main__":
    main()
