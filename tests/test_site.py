import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_site as site
from ipe_web_kit import journal, languages

FIRST_POST_DAY = date(2026, 11, 26)


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
        cls.files = site.expected_files(FIRST_POST_DAY)

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
        for slug, post in site.journal_posts().items():
            with self.subTest(post=slug):
                self.assertEqual(set(post["editions"]), set(languages.SUPPORTED))
                if image := post.get("image"):
                    self.assertTrue((site.ROOT / "assets" / image).is_file())
                for edition in post["editions"].values():
                    for field in ("title", "summary"):
                        self.assertTrue(edition[field].strip())
                    self.assertTrue(edition["body"])
                    self.assertTrue(all(paragraph.strip() for paragraph in edition["body"]))
                    if image:
                        self.assertTrue(edition["alt"].strip())
                ready = post["date"] <= FIRST_POST_DAY.isoformat() and journal.is_publishable(site.post_editions(slug, post))
                for lang in languages.SUPPORTED:
                    self.assertEqual(
                        site.route(lang, "journal/" + slug)[1:] + "index.html" in self.files,
                        ready,
                    )

    def test_approved_article_builds_with_image_and_localized_navigation(self):
        article = "ko/journal/heart-board/index.html"
        page = Page(self.files[article])
        self.assertIn(b"/ko/journal/heart-board/", self.files["ko/journal/index.html"])
        self.assertIn(b"/ko/journal/heart-board/", self.files["sitemap.xml"])
        self.assertTrue(page.tags("img")[0]["alt"])
        self.assertIn(urlsplit(page.tags("img")[0]["src"]).path[1:], self.files)

    def test_journal_release_respects_kst_date_and_all_language_reviews(self):
        posts = site.journal_posts()
        slug = "look-past-the-gap"
        post = posts[slug]
        due = date.fromisoformat(post["date"])
        for edition in post["editions"].values():
            edition.update(copy_review="iris", copy_review_date="2026-11-26")

        with patch.object(site, "journal_posts", return_value=posts):
            before = site.expected_files(FIRST_POST_DAY)
            on_date = site.expected_files(due)
            post["editions"]["ko"].pop("copy_review")
            pending = site.expected_files(due)

        for lang in languages.SUPPORTED:
            with self.subTest(lang=lang):
                url = site.route(lang, "journal/" + slug)
                index = site.route(lang, "journal")[1:] + "index.html"
                article = url[1:] + "index.html"
                for excluded in (before, pending):
                    self.assertNotIn(article, excluded)
                    self.assertNotIn(url.encode(), excluded[index])
                    self.assertNotIn(url.encode(), excluded["sitemap.xml"])
                self.assertIn(url.encode(), on_date[index])
                self.assertIn(url.encode(), on_date["sitemap.xml"])
                self.assertEqual(Page(on_date[index]).tags("time")[0]["datetime"], due.isoformat())
                self.assertEqual(Page(on_date[article]).tags("time")[0]["datetime"], due.isoformat())
        metadata = on_date["journal/" + slug + "/index.html"].decode()
        jsonld = metadata.split('<script type="application/ld+json">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(jsonld)["datePublished"], due.isoformat())


def run_main(*argv, today):
    out, err = io.StringIO(), io.StringIO()
    with patch.object(site, "today_kst", return_value=today), redirect_stdout(out), redirect_stderr(err):
        code = site.main(list(argv))
    return code, out.getvalue() + err.getvalue()


class BuildDateTest(unittest.TestCase):
    """검사는 build_meta.json 의 날짜로 비교한다 — 날이 바뀌어도 커밋된 public/ 이 깨지지 않는다."""

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        for name, value in (("PUBLIC", tmp / "public"), ("BUILD_META", tmp / "build_meta.json")):
            patcher = patch.object(site, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_committed_public_stays_green_on_later_days(self):
        with patch.object(site, "PUBLIC", site.ROOT / "public"), patch.object(site, "BUILD_META", site.ROOT / "build_meta.json"):
            built = site.read_build_date()
            for later in (built, date(2026, 11, 28), date(2026, 12, 9), date(2027, 1, 1)):
                with self.subTest(today=later):
                    self.assertEqual(run_main("--check", today=later), (0, f"{built} KST 공개 파일 {len(site.expected_files(built))}개 검증\n"))
                    self.assertEqual(run_main("--check", "--date", later.isoformat(), today=date(2000, 1, 1))[0], 0)

    def test_build_records_its_date_and_check_uses_it(self):
        self.assertEqual(run_main(today=FIRST_POST_DAY)[0], 0)
        self.assertEqual(site.read_build_date(), FIRST_POST_DAY)
        for later in (date(2026, 11, 28), date(2026, 12, 9)):
            with self.subTest(today=later):
                self.assertEqual(run_main("--check", today=later)[0], 0)
                self.assertEqual(run_main("--check", "--date", later.isoformat(), today=FIRST_POST_DAY)[0], 0)
        self.assertEqual(run_main("--date", "2026-12-09", today=FIRST_POST_DAY)[0], 0)
        self.assertEqual(site.read_build_date(), date(2026, 12, 9))
        self.assertEqual(run_main("--check", today=date(2026, 12, 9))[0], 0)

    def test_public_built_ahead_of_today_fails(self):
        run_main("--date", "2026-12-09", today=FIRST_POST_DAY)
        code, output = run_main("--check", today=date(2026, 12, 8))
        self.assertEqual(code, 1)
        self.assertIn("2026-12-09", output)

    def test_edited_public_fails(self):
        run_main(today=FIRST_POST_DAY)
        (site.PUBLIC / "index.html").write_text("changed", encoding="utf-8")
        code, output = run_main("--check", today=date(2026, 12, 9))
        self.assertEqual(code, 1)
        self.assertIn("생성물 불일치 index.html", output)

    def test_missing_build_meta_explains_how_to_regenerate(self):
        with self.assertRaises(SystemExit) as raised:
            run_main("--check", today=FIRST_POST_DAY)
        self.assertIn("build_site.py", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
