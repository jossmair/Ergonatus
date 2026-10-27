from scripts.package_sources import source_files


def test_source_archive_excludes_disposable_profiles_and_bytecode(tmp_path):
    public = tmp_path / "docs/validation/result.json"
    public.parent.mkdir(parents=True)
    public.write_text('{"success": true}', encoding="utf-8")
    for relative in ("docs/test-settings/preferences/settings.json", "app/__pycache__/main.pyc"):
        file = tmp_path / relative
        file.parent.mkdir(parents=True)
        file.write_text("private fixture", encoding="utf-8")
    files = source_files(tmp_path)
    assert public in files
    assert not any("test-settings" in file.parts or "__pycache__" in file.parts for file in files)
