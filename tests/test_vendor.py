import hashlib
import io

import pytest

from nooote import vendor


def _fake_download(data: bytes, monkeypatch, calls=None):
    def fake_urlopen(request, timeout=None):
        if calls is not None:
            calls.append(request.full_url)

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                self.close()
                return False

        return Response(data)

    monkeypatch.setattr(vendor.urllib.request, "urlopen", fake_urlopen)


def test_asset_paths_are_unique():
    paths = [asset.path for asset in vendor.ASSETS]

    assert len(paths) == len(set(paths))


def test_asset_digests_are_sha256_hex():
    for asset in vendor.ASSETS:
        assert len(asset.sha256) == 64
        int(asset.sha256, 16)
        assert asset.urls


def test_sync_downloads_missing_asset(tmp_path, monkeypatch):
    payload = b"console.log('hi');"
    asset = vendor.Asset(
        "demo.min.js",
        hashlib.sha256(payload).hexdigest(),
        ("https://example.test/demo.min.js",),
    )
    monkeypatch.setattr(vendor, "ASSETS", (asset,))
    _fake_download(payload, monkeypatch)

    written = vendor.sync(tmp_path)

    assert written == ["demo.min.js"]
    assert (tmp_path / "vendor" / "demo.min.js").read_bytes() == payload


def test_sync_keeps_current_file_without_network(tmp_path, monkeypatch):
    payload = b"already here"
    asset = vendor.Asset(
        "nested/demo.js",
        hashlib.sha256(payload).hexdigest(),
        ("https://example.test/nested/demo.js",),
    )
    monkeypatch.setattr(vendor, "ASSETS", (asset,))
    target = tmp_path / "vendor" / "nested" / "demo.js"
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)

    def fail(*args, **kwargs):
        raise AssertionError("network should not be used")

    monkeypatch.setattr(vendor.urllib.request, "urlopen", fail)

    assert vendor.sync(tmp_path) == []


def test_sync_replaces_corrupted_file(tmp_path, monkeypatch):
    payload = b"good"
    asset = vendor.Asset(
        "demo.js",
        hashlib.sha256(payload).hexdigest(),
        ("https://example.test/demo.js",),
    )
    monkeypatch.setattr(vendor, "ASSETS", (asset,))
    target = tmp_path / "vendor" / "demo.js"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupted")
    _fake_download(payload, monkeypatch)

    assert vendor.sync(tmp_path) == ["demo.js"]
    assert target.read_bytes() == payload


def test_sync_falls_back_to_next_mirror(tmp_path, monkeypatch):
    payload = b"mirrored"
    asset = vendor.Asset(
        "demo.js",
        hashlib.sha256(payload).hexdigest(),
        ("https://broken.test/demo.js", "https://working.test/demo.js"),
    )
    monkeypatch.setattr(vendor, "ASSETS", (asset,))
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        if "broken" in request.full_url:
            raise vendor.urllib.error.URLError("boom")

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                self.close()
                return False

        return Response(payload)

    monkeypatch.setattr(vendor.urllib.request, "urlopen", fake_urlopen)

    vendor.sync(tmp_path)

    assert calls == [
        "https://broken.test/demo.js",
        "https://working.test/demo.js",
    ]


def test_sync_rejects_digest_mismatch(tmp_path, monkeypatch):
    asset = vendor.Asset(
        "demo.js",
        hashlib.sha256(b"expected").hexdigest(),
        ("https://example.test/demo.js",),
    )
    monkeypatch.setattr(vendor, "ASSETS", (asset,))
    _fake_download(b"tampered", monkeypatch)

    with pytest.raises(RuntimeError):
        vendor.sync(tmp_path)

    assert not (tmp_path / "vendor" / "demo.js").exists()


def test_sync_app_is_skipped_by_env(tmp_path, monkeypatch):
    monkeypatch.setenv(vendor.SYNC_FLAG_ENV, "1")
    called = []
    monkeypatch.setattr(vendor, "sync", lambda *a, **k: called.append(a))

    class App:
        static_folder = str(tmp_path)

    vendor._synced_folders.clear()
    vendor.sync_app(App())

    assert called == []


def test_sync_app_runs_only_once_per_folder(tmp_path, monkeypatch):
    monkeypatch.delenv(vendor.SYNC_FLAG_ENV, raising=False)
    calls = []

    def fake_sync(static_folder, quiet=False):
        calls.append(static_folder)
        return []

    monkeypatch.setattr(vendor, "sync", fake_sync)

    class App:
        static_folder = str(tmp_path)

    vendor._synced_folders.clear()
    vendor.sync_app(App())
    vendor.sync_app(App())

    assert calls == [str(tmp_path)]


def test_missing_assets_reports_absent_files(tmp_path):
    (tmp_path / "vendor").mkdir()
    first = vendor.ASSETS[0]

    missing = vendor.missing_assets(tmp_path)

    assert first.path in missing
    assert len(missing) == len(vendor.ASSETS)


def test_main_reports_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(vendor, "sync", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nope")))

    assert vendor.main() == 1
    assert "sync failed" in capsys.readouterr().err


def test_vendor_assets_include_fontawesome():
    paths = {asset.path for asset in vendor.ASSETS}

    assert "fontawesome/css/fontawesome.min.css" in paths
    assert "fontawesome/css/solid.min.css" in paths
    assert "fontawesome/webfonts/fa-solid-900.woff2" in paths
    assert "LICENSE.fontawesome" in paths
