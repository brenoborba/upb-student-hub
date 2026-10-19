from upb.utils import save_debug


def test_save_debug_writes_file(tmp_path):
    d = tmp_path / "debug"
    save_debug(str(d), "site_abc.html", "<html></html>")
    assert (d / "site_abc.html").read_text(encoding="utf-8") == "<html></html>"


def test_save_debug_creates_directory(tmp_path):
    d = tmp_path / "nested" / "debug"
    save_debug(str(d), "x.html", "data")
    assert (d / "x.html").exists()


def test_save_debug_noop_when_none():
    save_debug(None, "x.html", "data")


def test_save_debug_overwrites(tmp_path):
    d = tmp_path / "debug"
    save_debug(str(d), "x.html", "first")
    save_debug(str(d), "x.html", "second")
    assert (d / "x.html").read_text(encoding="utf-8") == "second"
