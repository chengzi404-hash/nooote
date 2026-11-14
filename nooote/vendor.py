"""Download the third-party browser libraries served from ``static/vendor``.

``nooote/static/vendor`` is gitignored, so a fresh checkout has no third-party
files. Every app start calls :func:`sync`, which downloads only the files that
are missing or fail their SHA-256 check, verifying each download against the
pinned digest in :data:`ASSETS` before writing it to disk.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

VENDOR_DIR_NAME = "vendor"
SYNC_FLAG_ENV = "NOOOTE_SKIP_VENDOR_SYNC"
DOWNLOAD_TIMEOUT_SECONDS = 30
USER_AGENT = "nooote-vendor-sync"

CDNJS = "https://cdnjs.cloudflare.com/ajax/libs"
JSDELIVR = "https://cdn.jsdelivr.net/npm"
UNPKG = "https://unpkg.com"

MARKED = "marked@18.2.0"
HIGHLIGHT = "@highlightjs/cdn-assets@11.12.0"
HIGHLIGHT_PACKAGE = "highlight.js@11.12.0"
DOMPURIFY = "dompurify@3.4.17"
KATEX = "katex@0.18.10"
MERMAID = "mermaid@11.12.2"
FONT_AWESOME = "@fortawesome/fontawesome-free@7.3.1"


@dataclass(frozen=True)
class Asset:
    """One vendored file: where it lives, its digest, and trusted mirrors."""

    path: str
    sha256: str
    urls: tuple[str, ...]


KATEX_FONT_SHA256: dict[str, dict[str, str]] = {
    "KaTeX_AMS-Regular": {
        "woff2": "0cdd387c9590a1a9f9794560022dbb59654a7d86f187aa0c81495ad42d3a7308",
        "woff": "30da91e84c893f875e252689faebdc590b2871145e8adc7f9a9d4dbd8ce0b251",
        "ttf": "68534840bcfdd2bffb6f0e8deb48684dd01e7f04ea2813267577afb906de1d13",
    },
    "KaTeX_Caligraphic-Bold": {
        "woff2": "de7701e42cf1f4cf0b766c03fb27977207eee2f4fd5d76fa82188406da43ea4c",
        "woff": "1ae6bd7475590e97e7f145a89e09ccde322f7a6bc0b91607b1c8b8ee28290fed",
        "ttf": "07d8e303ce4fc12b4bb54f1004170dd190a1f3db45d400fe68060df3e0897268",
    },
    "KaTeX_Caligraphic-Regular": {
        "woff2": "5d53e70ad607c2352162dec9e0923fb54ecdafaccbf604cd8dcf7d00facb989b",
        "woff": "3398dd02302557a793f2863f88e02d96ce10df2abffa07c8e9fa90775116e65c",
        "ttf": "ed0b74372feefcbb9c0666b2e210da37b7e49fa7fbbf3eeb11db5f693dacfbb7",
    },
    "KaTeX_Fraktur-Bold": {
        "woff2": "74444efd593c005e3f4573b44524704c0af0a937fe911cca9e94068d0d140d3f",
        "woff": "9be7ceb88004ab8ad124082246fbfcca4091e36385d4ec6ed1df67375dad50fb",
        "ttf": "9163df9c7122432e6495b4229fa9071cf9ae86a758ae5efc4924ec2e1a6dbce1",
    },
    "KaTeX_Fraktur-Regular": {
        "woff2": "51814d270d06ff0255dba0799994fa4d8c84d11f09951d47595f4abb1f3602dc",
        "woff": "5e28753be717dac97f559f49bc10be9cf3c124ddcabda6659d11cb68febc6463",
        "ttf": "1e6f9579e90e2cac37f8f60a597c436e075c114385652b7cbeb0dec0421291b3",
    },
    "KaTeX_Main-Bold": {
        "woff2": "0f60d1b897938ec918c8ce073092411baf9438f6739465693ff18b0f9d20b021",
        "woff": "c76c5d696297d51b9cb1639c7da4334f0e7dec81b42b11213b5e25ef671bb822",
        "ttf": "138ac28d1663b3037e9c5f52371fa5c63d8324f4a38d22cd573e6ea3a3fd0cf8",
    },
    "KaTeX_Main-BoldItalic": {
        "woff2": "99cd42a3c072d918f2f44984a807cf7aa16e13545fd0875fc07c6c65f99e715b",
        "woff": "a6f7ec0d846ac7ad975adb8959c37ed49b94acbc4ae436db9ce9e20287e4a64c",
        "ttf": "70ee1f64a20f2048c21940ef46d0144fd215baa953ca69afd1e31e98544f708f",
    },
    "KaTeX_Main-Italic": {
        "woff2": "97479ca6cce906abc961ecac96faa5f9ca2e61b8e7670d475826bcdee9a7c267",
        "woff": "f1d6ef86f3b11a528bd5185199bd2443ecb2b0dead96d88674b5a2c12be24bdf",
        "ttf": "0d85ae7cc30f23790a7f1a58c4a112fdca8aae769b6ba11429af1d98b1b6cb3a",
    },
    "KaTeX_Main-Regular": {
        "woff2": "c2342cd8b869e01752a9321dc17213fc40d4d04c79688c1d43f2cf316abd7866",
        "woff": "c6368d87e8a1a3a5d337623d83d8dc4b868f242a9ad476237d6f8d1e0f168cdc",
        "ttf": "d0332f52868370fd83ae7fa46470f90c8f2eab2fcf12bc4f88080b340c95a830",
    },
    "KaTeX_Math-BoldItalic": {
        "woff2": "dc47344dbb6cb5b655c8460d561f4df5f501b90c804ad3c6cec65fe322351ab1",
        "woff": "850c0af5c2238497febaf5e461d880bf458c341f42f4f330f1b1ab5698b1998e",
        "ttf": "f9377ab0271cda59af24bcffbd46a4d0c8a3572ffafdbb38de2ad5ea7b0d5ee5",
    },
    "KaTeX_Math-Italic": {
        "woff2": "7af58c5ec8f132a2ddde9027c6d7814decce4d3b822a11192a42a20e2e973264",
        "woff": "8a8d244581371912b8f3f5a23e2437cb2a59cd9bcaebb0346e722c05737a2571",
        "ttf": "08ce98e51b04d58945a301e639e02b6998af29fdfd61a7b8afdd07bbfc479d4a",
    },
    "KaTeX_SansSerif-Bold": {
        "woff2": "e99ae51144bf1232efcc1bfe5add36262c6866b0faab24fa75740e1b98577a62",
        "woff": "ece03cfd83e22c212cdef66feb8442d25a083beb988db3f1883f3f9738d750ba",
        "ttf": "1ece03f79f95277d57dc7f6b435a74e1379b0d46104a8530286b60ff49369ea0",
    },
    "KaTeX_SansSerif-Italic": {
        "woff2": "00b26ac825e2095056396e0553b8ac26d3f8ad158c3826e28b4c45b385c4714a",
        "woff": "91ee67500cc0129aa0ace3ac5c61ff1692102f0f31d02b69347fba35dcb75bf2",
        "ttf": "3931dd81faed86ba021bb2bbdc36f5bed9a38d6b4f4077aca59b265aa1b02083",
    },
    "KaTeX_SansSerif-Regular": {
        "woff2": "68e8c73ef42afd3ccec58bf0fba302cce448938e7fc020a5e31f8a952eee1342",
        "woff": "11e4dc8a6471ff6d6ee561d53d10fde8f7489e798257ff449c5d37c197435605",
        "ttf": "f36ea897e19f4a2e571d1e900e4e3710e438deb05a842486045ba0a3e616a4ad",
    },
    "KaTeX_Script-Regular": {
        "woff2": "036d4e95149b69ff9bcc0cd55771efeb25ffa3947293e69acd78d5ac328c684b",
        "woff": "d96cdf2b3bdd4d64a8fd5f74a4c467f123a8a73931cd435889f08ffaf9bf947a",
        "ttf": "1c67f068fea8bb09bf099c088b1cf64bd27516a6e07f4684344873564bb66a67",
    },
    "KaTeX_Size1-Regular": {
        "woff2": "6b47c40166b6dbe21a5dfca7718413f2147fd2399be1ba605d8ad39cedf25dfe",
        "woff": "c943cc986384f59e86bea5fd7dc50a9c4dfe567a7c05eb40d6790720dead97c9",
        "ttf": "95b6d2f1a50173bfedb8c63e1d1c99b10427d0a4df4201cb44513b226951a22b",
    },
    "KaTeX_Size2-Regular": {
        "woff2": "d04c54219f9eaec6d4d4fd42dfb28785975a4794d6b2fc71e566b9cd6db842dd",
        "woff": "2014c523c3210bcc166648c4d4cc57f05b747df07a24277bf71c51e67dc79e3d",
        "ttf": "a6b2099fb555c60e3a0db3a08842ebf1d732c6eb4e4bf44913613bed4fc4e39b",
    },
    "KaTeX_Size3-Regular": {
        "woff2": "73d591271b1604960cb10bb90fee021670af7297017e0e98480b332d11f51995",
        "woff": "6ab6b62e9b62dae2c00dd90f791bd10950be0ecc3490d7d6045f51c2e8fe0949",
        "ttf": "500e04d54f0d51666332c9d2089aa803be22aa878eca539e59fa53c6e522b082",
    },
    "KaTeX_Size4-Regular": {
        "woff2": "a4af7d414440a1c1790825cfb700cf9cf43b0f2c4b04f0ebc523011ad9853ec0",
        "woff": "99f9c6750b489c9462bf04900bd3f939df9b829339daaaaa99ef5495cdddea58",
        "ttf": "c647367d1dd4e162468717d020e1fc0f1dc5c26ebfdffbe55261713bf88c5877",
    },
    "KaTeX_Typewriter-Regular": {
        "woff2": "71d517d67827787cfabdf186914cc3358eda539e37931941f2b2fd4a21f68c0b",
        "woff": "e14fed02b1aba7ce9f5afd5844b5d0321b22351febc720e0de8b8723527609f7",
        "ttf": "f01f3e87d9c6a61c0c081ceb577abd864eb00a612f7ac1620dd6915fad2ef5aa",
    },
}


def _katex_font_assets() -> list[Asset]:
    assets: list[Asset] = []
    for stem, digests in KATEX_FONT_SHA256.items():
        for suffix, sha256 in digests.items():
            urls = [f"{JSDELIVR}/{KATEX}/dist/fonts/{stem}.{suffix}"]
            if suffix != "ttf":
                urls.insert(0, f"{CDNJS}/KaTeX/0.18.10/fonts/{stem}.{suffix}")
            assets.append(Asset(f"katex/fonts/{stem}.{suffix}", sha256, tuple(urls)))
    return assets


ASSETS: tuple[Asset, ...] = (
    Asset(
        "marked.min.js",
        "392f4df89533b50f1dadff3f6dc0952350bd39c9f17def50a0374ef47d6147ef",
        (
            f"{CDNJS}/marked/18.2.0/lib/marked.umd.js",
            f"{JSDELIVR}/{MARKED}/lib/marked.umd.js",
        ),
    ),
    Asset(
        "highlight.min.js",
        "8ab71eb09c51f501e5e25157d9cff100e46cc29bcbfc744d0b746d451fca7f53",
        (
            f"{CDNJS}/highlight.js/11.12.0/highlight.min.js",
            f"{JSDELIVR}/{HIGHLIGHT}/highlight.min.js",
        ),
    ),
    Asset(
        "purify.min.js",
        "cd37898f9782adf54820c413191b5691803f0f137c799d6edcfd38523b4c2c31",
        (
            f"{CDNJS}/dompurify/3.4.17/purify.min.js",
            f"{JSDELIVR}/{DOMPURIFY}/dist/purify.min.js",
        ),
    ),
    Asset(
        "github.min.css",
        "3a9a5def8b9c311e5ae43abde85c63133185eed4f0d9f67fea4b00a8308cf066",
        (
            f"{CDNJS}/highlight.js/11.12.0/styles/github.min.css",
            f"{JSDELIVR}/{HIGHLIGHT}/styles/github.min.css",
        ),
    ),
    Asset(
        "github-dark.min.css",
        "9f208d022102b1d0c7aebfecd8e42ca7997d5de636649d2b31ea63093d809019",
        (
            f"{CDNJS}/highlight.js/11.12.0/styles/github-dark.min.css",
            f"{JSDELIVR}/{HIGHLIGHT}/styles/github-dark.min.css",
        ),
    ),
    Asset(
        "katex/katex.min.js",
        "608ba65190845e9a9b6865ec75cd5d04fa9bc1ef86a6d23e6b01340d5f55eee3",
        (
            f"{CDNJS}/KaTeX/0.18.10/katex.min.js",
            f"{JSDELIVR}/{KATEX}/dist/katex.min.js",
        ),
    ),
    Asset(
        "katex/katex.min.css",
        "f76ac5391ddb3465afbff9f22394841ed065f5f45b5444c2d120b5126b6d56a5",
        (
            f"{CDNJS}/KaTeX/0.18.10/katex.min.css",
            f"{JSDELIVR}/{KATEX}/dist/katex.min.css",
        ),
    ),
    Asset(
        "mermaid/mermaid.min.js",
        "d0830a6c05546e9edb8fe20a8f545f3e0dc7c4c3134d584bad9c13a99d7a71e0",
        (
            f"{CDNJS}/mermaid/11.12.2/mermaid.min.js",
            f"{JSDELIVR}/{MERMAID}/dist/mermaid.min.js",
        ),
    ),
    Asset(
        "fontawesome/css/fontawesome.min.css",
        "405bfb2a5312e363b88650a68ed90b6c06c41d5cfa3cbf5c68251cafafb3c078",
        (
            f"{CDNJS}/font-awesome/7.3.1/css/fontawesome.min.css",
            f"{JSDELIVR}/{FONT_AWESOME}/css/fontawesome.min.css",
        ),
    ),
    Asset(
        "fontawesome/css/solid.min.css",
        "01219b97103029774a3e8cb1b22803490beec1df828895dfd9c5fd0d4798da25",
        (
            f"{CDNJS}/font-awesome/7.3.1/css/solid.min.css",
            f"{JSDELIVR}/{FONT_AWESOME}/css/solid.min.css",
        ),
    ),
    Asset(
        "fontawesome/webfonts/fa-solid-900.woff2",
        "24e5fae26b41c08b2df81c91669f5aaae71d81a84a4713fc56b5c621b78dd456",
        (
            f"{CDNJS}/font-awesome/7.3.1/webfonts/fa-solid-900.woff2",
            f"{JSDELIVR}/{FONT_AWESOME}/webfonts/fa-solid-900.woff2",
        ),
    ),
    Asset(
        "LICENSE.marked",
        "8e3a3f82f59a60958f56ca08f445647c32a4733dc7ca6c2c46f6eb898471ab9c",
        (
            f"{JSDELIVR}/{MARKED}/LICENSE",
            f"{UNPKG}/{MARKED}/LICENSE",
        ),
    ),
    Asset(
        "LICENSE.highlight.js",
        "6c081431591d9df696c82dc598fe1423765b8a299b200ed00b281afd0f64c490",
        (f"{JSDELIVR}/{HIGHLIGHT_PACKAGE}/LICENSE",),
    ),
    Asset(
        "LICENSE.dompurify",
        "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
        (f"{JSDELIVR}/{DOMPURIFY}/LICENSE",),
    ),
    Asset(
        "katex/LICENSE",
        "766ccc1f306c885aa45542a9846bbd0a505b27a0374f146778171c2254ce18e3",
        (f"{JSDELIVR}/{KATEX}/LICENSE",),
    ),
    Asset(
        "mermaid/LICENSE",
        "ec9fb67dcb25eccc416ed56e1aab819222c805a2a4bfe4cb19e7556bf2ffde80",
        (f"{JSDELIVR}/{MERMAID}/LICENSE",),
    ),
    Asset(
        "LICENSE.fontawesome",
        "20c6f40715a567c97b80f6944beb8bb325835cab47ea7dcab89ee3b8e077eced",
        (f"{JSDELIVR}/{FONT_AWESOME}/LICENSE.txt",),
    ),
    *_katex_font_assets(),
)


def vendor_dir(static_folder: Path | str) -> Path:
    """Return the directory that holds the vendored libraries."""
    return Path(static_folder) / VENDOR_DIR_NAME


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_current(path: Path, asset: Asset) -> bool:
    return path.is_file() and _sha256(path) == asset.sha256


def _download(asset: Asset) -> bytes:
    failures: list[str] = []
    for url in asset.urls:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                data = response.read()
        except (urllib.error.URLError, OSError) as error:
            failures.append(f"{url} ({error})")
            continue

        actual = hashlib.sha256(data).hexdigest()
        if actual != asset.sha256:
            failures.append(f"{url} (sha256 {actual})")
            continue

        return data

    raise RuntimeError(f"cannot fetch {asset.path}: " + "; ".join(failures))


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".part")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def sync(static_folder: Path | str, *, quiet: bool = False) -> list[str]:
    """Ensure every vendored asset exists and matches its pinned digest.

    Returns the paths (relative to the vendor directory) that were written.
    Files that already match are left alone, so repeated calls are cheap.
    """
    root = vendor_dir(static_folder)
    downloaded: list[str] = []

    for asset in ASSETS:
        target = root / asset.path
        if _is_current(target, asset):
            continue

        _write(target, _download(asset))
        downloaded.append(asset.path)
        if not quiet:
            print(f"vendor: downloaded {asset.path}", file=sys.stderr)

    return downloaded


_synced_folders: set[str] = set()


def sync_app(app) -> None:
    """Sync the vendor directory for a Flask app, once per process."""
    if os.environ.get(SYNC_FLAG_ENV):
        return

    root = vendor_dir(app.static_folder)
    key = str(root.resolve())
    if key in _synced_folders:
        return
    _synced_folders.add(key)

    try:
        downloaded = sync(app.static_folder)
    except RuntimeError as error:
        print(f"vendor: sync failed: {error}", file=sys.stderr)
        return

    if downloaded:
        print(f"vendor: synced {len(downloaded)} file(s) into static/{VENDOR_DIR_NAME}", file=sys.stderr)


def missing_assets(static_folder: Path | str) -> list[str]:
    """Return vendored paths that are absent or fail their digest check."""
    root = vendor_dir(static_folder)
    return [asset.path for asset in ASSETS if not _is_current(root / asset.path, asset)]


def main() -> int:
    """Download every missing asset; usable as ``python -m nooote.vendor``."""
    static_folder = Path(__file__).resolve().parent / "static"
    try:
        downloaded = sync(static_folder)
    except RuntimeError as error:
        print(f"vendor: sync failed: {error}", file=sys.stderr)
        return 1

    print(f"vendor: {len(downloaded)} file(s) written, {len(ASSETS) - len(downloaded)} already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
