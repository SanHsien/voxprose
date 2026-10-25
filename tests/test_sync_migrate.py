"""同步目錄遷移不能刪掉來源資料。

Regression: ui/settings/sync_page.py 的 `_migrate_to_sync` 對 `dst` 先 rmtree 再
copytree。使用者選到本機資料夾本身（%APPDATA%\\VoxProse）或其子／父目錄時，
dst 與 src 是同一個目錄：rmtree 先把來源刪光，copytree 再因來源不存在而失敗，
靈魂情境／詞彙／記憶／統計全部永久消失。
"""
from utils.sync_migrate import migrate_to_sync


def _make_data(app_dir):
    for folder in ("soul", "vocab", "memory", "stats"):
        d = app_dir / folder
        d.mkdir(parents=True)
        (d / "data.txt").write_text(f"{folder}-data", encoding="utf-8")
    (app_dir / "ai_permanent_memory.md").write_text("perm", encoding="utf-8")


def test_normal_migration_copies_folders_and_files(tmp_path):
    app, target = tmp_path / "app", tmp_path / "sync"
    _make_data(app)
    target.mkdir()

    migrate_to_sync(app, target)

    assert (target / "soul" / "data.txt").read_text(encoding="utf-8") == "soul-data"
    assert (target / "memory" / "data.txt").read_text(encoding="utf-8") == "memory-data"
    assert (target / "ai_permanent_memory.md").read_text(encoding="utf-8") == "perm"
    assert (app / "soul" / "data.txt").exists()  # 來源保留


def test_target_equal_to_app_dir_does_not_delete_source(tmp_path):
    app = tmp_path / "app"
    _make_data(app)

    migrate_to_sync(app, app)

    for folder in ("soul", "vocab", "memory", "stats"):
        assert (app / folder / "data.txt").read_text(encoding="utf-8") == f"{folder}-data"


def test_target_inside_a_source_folder_does_not_delete_or_recurse(tmp_path):
    app = tmp_path / "app"
    _make_data(app)

    migrate_to_sync(app, app / "soul")

    assert (app / "soul" / "data.txt").read_text(encoding="utf-8") == "soul-data"
    assert (app / "vocab" / "data.txt").exists()


def test_existing_destination_is_replaced_by_source_copy(tmp_path):
    app, target = tmp_path / "app", tmp_path / "sync"
    _make_data(app)
    (target / "soul").mkdir(parents=True)
    (target / "soul" / "stale.txt").write_text("stale", encoding="utf-8")

    migrate_to_sync(app, target)

    assert not (target / "soul" / "stale.txt").exists()
    assert (target / "soul" / "data.txt").exists()
