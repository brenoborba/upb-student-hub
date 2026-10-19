from types import SimpleNamespace

from bs4 import BeautifulSoup

from upb.sites import (
    _collect_all_sites,
    _collect_favorites,
    _collect_site,
    discover_sites,
)


def test_collect_site_basic():
    soup = BeautifulSoup(
        '<a href="/portal/site/abc123" title="Matemática">Matemática</a>',
        "html.parser",
    )
    sites = {}
    _collect_site(soup.find("a"), sites)
    assert sites == {"abc123": "Matemática"}


def test_collect_site_uses_text_when_no_title():
    soup = BeautifulSoup('<a href="/portal/site/abc123">Matemática</a>', "html.parser")
    sites = {}
    _collect_site(soup.find("a"), sites)
    assert sites == {"abc123": "Matemática"}


def test_collect_site_skips_prefixes():
    for prefix in ("!", "~"):
        soup = BeautifulSoup(f'<a href="/portal/site/{prefix}abc">X</a>', "html.parser")
        sites = {}
        _collect_site(soup.find("a"), sites)
        assert sites == {}


def test_collect_site_ignores_non_site_href():
    soup = BeautifulSoup('<a href="/portal/other">X</a>', "html.parser")
    sites = {}
    _collect_site(soup.find("a"), sites)
    assert sites == {}


def test_collect_site_dedupes():
    soup = BeautifulSoup('<a href="/portal/site/abc" title="A">A</a>', "html.parser")
    sites = {"abc": "A"}
    _collect_site(soup.find("a"), sites)
    assert sites == {"abc": "A"}


def test_discover_sites_favorites_only():
    html = """
    <div id="topnav">
      <a href="/portal/site/a1" title="Course A">A</a>
    </div>
    <div id="allSitesMenu">
      <a href="/portal/site/b2" title="Course B">B</a>
    </div>
    """
    client = SimpleNamespace(get=lambda path: SimpleNamespace(text=html))
    assert discover_sites(client, favorites_only=True) == {"a1": "Course A"}


def test_discover_sites_all_sites():
    html = """
    <div id="topnav">
      <a href="/portal/site/a1" title="Course A">A</a>
    </div>
    <div id="allSitesMenu">
      <a href="/portal/site/b2" title="Course B">B</a>
    </div>
    """
    client = SimpleNamespace(get=lambda path: SimpleNamespace(text=html))
    assert discover_sites(client, favorites_only=False) == {
        "a1": "Course A",
        "b2": "Course B",
    }


def test_collect_favorites_fallback_by_class():
    html = """
    <div id="other">
      <a class="sitesnav__menuitem--link" href="/portal/site/a1" title="Course A">A</a>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    sites = {}
    _collect_favorites(soup, sites)
    assert sites == {"a1": "Course A"}


def test_collect_all_sites_last_resort():
    html = '<a href="/portal/site/c3" title="Course C">C</a>'
    soup = BeautifulSoup(html, "html.parser")
    sites = {}
    _collect_all_sites(soup, sites)
    assert sites == {"c3": "Course C"}
