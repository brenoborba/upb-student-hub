from __future__ import annotations

import re

from bs4 import BeautifulSoup

from upb.utils import save_debug

SITE_HREF_RE = re.compile(r"/portal/site/([^/?#]+)")

SKIP_PREFIXES = ("!", "~")

# Favorites are the top-nav tabs; the full list lives in the "More sites" drawer.
FAVORITES_CONTAINER_IDS = ("topnav", "sitesNav")
ALL_SITES_CONTAINER_IDS = ("allSitesMenu", "otherSitesMenu", "allSites")
FAVORITE_LINK_CLASS_HINT = "sitesnav__menuitem--link"


def discover_sites(
    client,
    favorites_only: bool = True,
    debug_dir: str | None = None,
) -> dict[str, str]:
    """Return {site_id: title} for the user's sites.

    With ``favorites_only=True`` only the favorited sites (top tabs) are
    returned; otherwise every enrolled site (including past semesters) is
    collected from the "More sites" drawer.
    """
    resp = client.get("portal")
    save_debug(debug_dir, "home.html", resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")
    sites: dict[str, str] = {}

    _collect_favorites(soup, sites)

    if not favorites_only:
        _collect_all_sites(soup, sites)

    return sites


def _collect_favorites(soup: BeautifulSoup, sites: dict[str, str]) -> None:
    container = None
    for cid in FAVORITES_CONTAINER_IDS:
        container = soup.find(id=cid)
        if container is not None:
            break

    if container is not None:
        for a in container.find_all("a", href=True):
            _collect_site(a, sites)
        return

    # Fallback: favorite-tab links, excluding the "More sites" drawer.
    for a in soup.find_all("a", href=True):
        if _in_drawer(a):
            continue
        classes = " ".join(a.get("class", [])).lower()
        if FAVORITE_LINK_CLASS_HINT in classes:
            _collect_site(a, sites)


def _collect_all_sites(soup: BeautifulSoup, sites: dict[str, str]) -> None:
    for cid in ALL_SITES_CONTAINER_IDS:
        container = soup.find(id=cid)
        if container is None:
            continue
        for a in container.find_all("a", href=True):
            _collect_site(a, sites)

    # Last resort: scan the whole page for site links.
    for a in soup.find_all("a", href=True):
        _collect_site(a, sites)


def _in_drawer(a) -> bool:
    for cid in ALL_SITES_CONTAINER_IDS:
        if a.find_parent(id=cid) is not None:
            return True
    return False


def _collect_site(a, sites: dict[str, str]) -> None:
    m = SITE_HREF_RE.search(a.get("href", ""))
    if not m:
        return
    site_id = m.group(1)
    if site_id.startswith(SKIP_PREFIXES):
        return
    title = (a.get("title") or a.get_text(strip=True)).strip()
    if site_id and title and site_id not in sites:
        sites[site_id] = title
