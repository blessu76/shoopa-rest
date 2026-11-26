import hashlib
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_site as site
from ipe_web_kit import journal, languages


class Page(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.elements = []
        self.feed(content.decode())

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def tags(self, tag):
        return [attrs for name, attrs in self.elements if name == tag]


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = site.expected_files()

    def test_every_locale_has_copy_and_five_localized_pages(self):
        translations = {file.stem for file in (site.ROOT / "content").glob("*.json")}
        self.assertEqual(translations, set(languages.SUPPORTED))
        for lang in languages.SUPPORTED:
            copy = site.read_json(site.ROOT / "content" / f"{lang}.json")
            self.assertEqual(len(copy["home"]["rules"]), 3)
            for section in site.PAGES:
                with self.subTest(lang=lang, section=section):
                    path = site.route(lang, section)
                    content = self.files[path[1:] + "index.html"]
                    page = Page(content)
                    self.assertEqual(page.tags("html")[0]["lang"], lang)
                    self.assertEqual(len(page.tags("h1")), 1)
                    self.assertEqual(len(page.tags("main")), 1)
                    self.assertEqual(
                        {a["hreflang"]: a["href"] for a in page.tags("link") if a["rel"] == "alternate"},
                        {**site.variants(section), "x-default": site.BASE + site.route("en", section)},
                    )
                    self.assertEqual(
                        [a["href"] for a in page.tags("link") if a["rel"] == "canonical"],
                        [site.BASE + path],
                    )
                    self.assertEqual(
                        {a["lang"]: a["value"] for a in page.tags("option")},
                        {code: site.route(code, section) for code in languages.SUPPORTED},
                    )
                    for link in page.tags("a"):
                        href = link.get("href", "")
                        if href.startswith("/") and not href.startswith("//"):
                            self.assertIn(urlsplit(href).path[1:] + "index.html", self.files)
                    if section in ("", "play"):
                        self.assertEqual(content.decode().count(copy["coming"]), 2 if section == "" else 3)

    def test_privacy_describes_platform_services_billing_and_hosting(self):
        for lang in languages.SUPPORTED:
            with self.subTest(lang=lang):
                content = self.files[site.route(lang, "privacy")[1:] + "index.html"].decode()
                for provider in ("iCloud", "Game Center", "Google Play", "App Store", "GitHub Pages"):
                    self.assertIn(provider, content)
                self.assertIn("IP", content)
                self.assertIn("mailto:" + site.CONTACT, content)

    def test_embedded_assets_are_versioned(self):
        page = Page(self.files["index.html"])
        assets = [a["href"] for a in page.tags("link") if a["rel"] in ("stylesheet", "icon")]
        assets.extend(a["src"] for a in page.tags("script"))
        for asset in assets:
            with self.subTest(asset=asset):
                parts = urlsplit(asset)
                digest = hashlib.sha256(self.files[parts.path[1:]]).hexdigest()[:12]
                self.assertEqual(parse_qs(parts.query), {"v": [digest]})

    def test_sitemap_matches_public_pages(self):
        document = ElementTree.fromstring(self.files["sitemap.xml"])
        urls = {el.text for el in document.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
        paths = [name[:-len("index.html")] for name in self.files if name.endswith("index.html")]
        self.assertEqual(urls, {f"{site.BASE}/{path}" for path in paths})

    def test_journal_editions_and_review_gate(self):
        for path in (site.ROOT / "content/journal").glob("*.json"):
            with self.subTest(post=path.stem):
                post = site.read_json(path)
                self.assertEqual(set(post["editions"]), set(languages.SUPPORTED))
                self.assertTrue((site.ROOT / "assets" / post["image"]).is_file())
                for edition in post["editions"].values():
                    self.assertTrue(all(edition[key] for key in ("title", "summary", "alt", "body")))
                ready = journal.is_publishable(site.post_editions(path.stem, post))
                for lang in languages.SUPPORTED:
                    self.assertEqual(
                        site.route(lang, "journal/" + path.stem)[1:] + "index.html" in self.files,
                        ready,
                    )

    def test_approved_article_builds_with_image_and_localized_navigation(self):
        path = site.ROOT / "content/journal/heart-board.json"
        read_json = site.read_json

        def approved_copy(source):
            data = read_json(source)
            if source == path:
                for edition in data["editions"].values():
                    edition.update(copy_review="iris", copy_review_date="2026-11-26")
            return data

        with patch.object(site, "read_json", side_effect=approved_copy):
            files = site.expected_files()
        article = "ko/journal/heart-board/index.html"
        page = Page(files[article])
        self.assertIn(b"/ko/journal/heart-board/", files["ko/journal/index.html"])
        self.assertIn(b"/ko/journal/heart-board/", files["sitemap.xml"])
        self.assertTrue(page.tags("img")[0]["alt"])
        self.assertIn(urlsplit(page.tags("img")[0]["src"]).path[1:], files)


if __name__ == "__main__":
    unittest.main()
