import io
import re
import zipfile
from pathlib import Path

import pytest

from tools.verify_release_zip import (
    REQUIRED_SUFFIXES,
    main,
    validate_release_zip,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_zip(path: Path, names: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, b"test")


def test_release_zip_accepts_utf8_required_names(tmp_path):
    archive_path = tmp_path / "good.zip"
    _write_zip(
        archive_path,
        [f"ShengChengWen-Windows-v3.4/{suffix}" for suffix in REQUIRED_SUFFIXES],
    )

    assert validate_release_zip(archive_path) == []


def test_release_zip_rejects_question_mark_names(tmp_path):
    archive_path = tmp_path / "bad.zip"
    names = [
        f"ShengChengWen-Windows-v3.4/{suffix}"
        for suffix in sorted(REQUIRED_SUFFIXES)
    ]
    names[0] = "ShengChengWen-Windows-v3.4/?????.txt"
    _write_zip(archive_path, names)

    errors = validate_release_zip(archive_path)

    assert any("非法或已損壞檔名" in error for error in errors)
    assert any("必要檔案" in error for error in errors)


def test_release_zip_rejects_missing_required_resource(tmp_path):
    archive_path = tmp_path / "missing.zip"
    names = [f"ShengChengWen-Windows-v3.4/{suffix}" for suffix in REQUIRED_SUFFIXES]
    names.pop()
    _write_zip(archive_path, names)

    errors = validate_release_zip(archive_path)

    assert any("必要檔案" in error for error in errors)


def test_release_zip_rejects_crc_corruption(tmp_path):
    archive_path = tmp_path / "corrupt.zip"
    _write_zip(
        archive_path,
        [f"ShengChengWen-Windows-v3.4/{suffix}" for suffix in REQUIRED_SUFFIXES],
    )
    data = archive_path.read_bytes()
    assert b"test" in data
    archive_path.write_bytes(data.replace(b"test", b"tEst", 1))

    errors = validate_release_zip(archive_path)

    assert any("CRC 驗證失敗" in error for error in errors)


def test_release_zip_rejects_duplicate_required_resource(tmp_path):
    archive_path = tmp_path / "duplicate.zip"
    names = [
        f"ShengChengWen-Windows-v3.4/{suffix}"
        for suffix in sorted(REQUIRED_SUFFIXES)
    ]
    names.append(names[0])
    with pytest.warns(UserWarning, match="Duplicate name"):
        _write_zip(archive_path, names)

    errors = validate_release_zip(archive_path)

    assert any("重複 entry" in error for error in errors)
    assert any("應恰好出現一次，實際 2 次" in error for error in errors)


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("not-a-zip.zip", b"this is not a zip archive"),
        ("truncated.zip", b"PK\x03\x04incomplete"),
    ],
)
def test_release_zip_rejects_unreadable_archives(tmp_path, filename, payload):
    archive_path = tmp_path / filename
    archive_path.write_bytes(payload)

    errors = validate_release_zip(archive_path)

    assert len(errors) == 1
    assert errors[0].startswith("無法讀取 ZIP：")


def test_release_zip_rejects_missing_path_and_cli_returns_failure(
    tmp_path, capsys
):
    missing = tmp_path / "missing.zip"

    errors = validate_release_zip(missing)
    exit_code = main([str(missing)])
    captured = capsys.readouterr()

    assert len(errors) == 1
    assert errors[0].startswith("無法讀取 ZIP：")
    assert exit_code == 1
    assert f"[FAIL] {missing}" in captured.out
    assert "無法讀取 ZIP：" in captured.out


def test_release_zip_cli_escapes_legacy_encoded_names(tmp_path, monkeypatch):
    """未設 UTF-8 flag 的舊編碼檔名，不得讓 cp950 主控台輸出再崩潰。"""
    archive_path = tmp_path / "legacy-name.zip"
    placeholder = "ShengChengWen-Windows-v3.4/" + "X" * 10 + ".txt"
    _write_zip(archive_path, [placeholder])

    legacy_name = (
        b"ShengChengWen-Windows-v3.4/"
        + "可攜版說明".encode("cp950")
        + b".txt"
    )
    data = archive_path.read_bytes()
    encoded_placeholder = placeholder.encode("ascii")
    assert len(legacy_name) == len(encoded_placeholder)
    assert data.count(encoded_placeholder) == 2
    archive_path.write_bytes(data.replace(encoded_placeholder, legacy_name))

    output_bytes = io.BytesIO()
    output = io.TextIOWrapper(output_bytes, encoding="cp950")
    monkeypatch.setattr("sys.stdout", output)

    assert main([str(archive_path)]) == 1
    output.flush()
    rendered = output_bytes.getvalue().decode("cp950")
    assert "\\x" in rendered or "\\u" in rendered


def test_release_zip_accepts_zip64_entry_count(tmp_path):
    archive_path = tmp_path / "zip64.zip"
    required = [
        f"ShengChengWen-Windows-v3.4/{suffix}"
        for suffix in sorted(REQUIRED_SUFFIXES)
    ]
    with zipfile.ZipFile(archive_path, "w", allowZip64=True) as archive:
        for name in required:
            archive.writestr(name, b"")
        for index in range(65_536 - len(required)):
            archive.writestr(f"ShengChengWen-Windows-v3.4/empty/{index}", b"")

    assert b"PK\x06\x06" in archive_path.read_bytes()
    assert validate_release_zip(archive_path) == []


def test_release_packager_uses_unicode_safe_zip_writer():
    script = (ROOT / "release_win.ps1").read_text(encoding="utf-8")

    assert "System.IO.Compression.ZipArchive]::new" in script
    assert "& tar.exe" not in script
    assert 'version = "(\\d+\\.\\d+\\.\\d+)"' in script
    assert 'v$Version' in script
    assert "VerShort" not in script


def test_release_workflow_validates_zip_before_hash_and_upload():
    workflow = (
        ROOT / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")

    validation = workflow.index("tools\\verify_release_zip.py")
    hashing = workflow.index("產生 SHA256 校驗檔")
    upload = workflow.index("actions/upload-artifact")
    assert validation < hashing < upload


def test_release_version_metadata_stays_in_sync():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    paths = (ROOT / "paths.py").read_text(encoding="utf-8")
    installer = (ROOT / "voicetype_installer.iss").read_text(encoding="utf-8")

    version = re.search(r'^version = "(\d+\.\d+\.\d+)"$', pyproject, re.MULTILINE)
    version_name = re.search(r'^VERSION_NAME = "V(\d+\.\d+\.\d+) ', paths, re.MULTILINE)
    build_id = re.search(r'^BUILD_ID = "BUILD-(\d+)-STABLE"$', paths, re.MULTILINE)
    installer_version = re.search(
        r'^#define MyAppVersion "(\d+\.\d+\.\d+)"$', installer, re.MULTILINE
    )
    installer_filename = re.search(
        r"^OutputBaseFilename=ShengChengWen-Windows-Setup-v(\d+\.\d+\.\d+)$",
        installer,
        re.MULTILINE,
    )

    assert all(
        (version, version_name, build_id, installer_version, installer_filename)
    )
    expected = version.group(1)
    assert version_name.group(1) == expected
    assert installer_version.group(1) == expected
    assert installer_filename.group(1) == expected
    assert build_id.group(1) == expected.replace(".", "") + "0"
