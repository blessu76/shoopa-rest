#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
sys.path.insert(0, str(ROOT / "vendor"))

from ipe_web_kit import ASSETS, journal, langswitch, languages, seo
from ipe_web_kit.seo import esc

DOMAIN = "shoopa.ipe.rest"
BASE = f"https://{DOMAIN}"
CONTACT = "ipe.haven@gmail.com"
PAGES = ("", "play", "journal", "privacy", "terms")
BOARD = (".u.u.", "llurr", "lldrr", ".ldr.", "..d..")


def route(lang, page=""):
    prefix = "" if lang == languages.DEFAULT else lang + "/"
    return "/" + prefix + (page + "/" if page else "")


def variants(page):
    return {lang: BASE + route(lang, page) for lang in languages.SUPPORTED}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def board():
    tiles = {"u": "up", "r": "right", "d": "down", "l": "left", ".": "empty"}
    cells = [
        f'<span class="tile {tiles[cell]}"></span>'
        for row in BOARD for cell in row
    ]
    return '<div class="board" aria-hidden="true">' + "".join(cells) + '</div>'


def page_link(lang, labels, page, current):
    active = ' aria-current="page"' if current == page else ""
    return f'<a href="{route(lang, page)}"{active}>{esc(labels[page])}</a>'


def header(lang, page, copy):
    labels = copy["nav"]
    links = "".join(page_link(lang, labels, name, page) for name in ("play", "journal"))
    select = langswitch.select_html(lang, lambda code: route(code, page))
    return f'''<header class="site-header">
  <div class="wrap topbar">
    <a class="brand" href="{route(lang)}"><span class="brand-mark" aria-hidden="true"></span>{esc(copy["brand"])}</a>
    <nav class="desktop-nav" aria-label="{esc(labels["menu"])}">{links}</nav>
    <div class="header-controls">
      {select}
      <details class="mobile-nav">
        <summary><span class="menu-icon" aria-hidden="true"></span><span class="sr-only">{esc(labels["menu"])}</span></summary>
        <nav aria-label="{esc(labels["menu"])}">{links}</nav>
      </details>
    </div>
  </div>
</header>'''


def footer(lang, page, copy):
    labels = copy["nav"]
    studio_url = "https://ipe.rest/" if lang == "en" else f"https://ipe.rest/?lang={lang}"
    links = "".join(page_link(lang, labels, name, page) for name in PAGES[1:])
    return f'''<footer class="site-footer">
  <div class="wrap footer-row">
    <a class="studio" href="{studio_url}">ipe Studio</a>
    <nav aria-label="{esc(labels["footer"])}">{links}</nav>
  </div>
</footer>'''


def home(lang, copy):
    content = copy["home"]
    rules = "".join(
        f'<li class="rule {icon}"><span class="rule-icon" aria-hidden="true">{glyph}</span>'
        f'<h3>{esc(title)}</h3><p>{esc(body)}</p></li>'
        for (icon, glyph), (title, body) in zip(
            (("path", "↗"), ("combo", "ϟ"), ("hearts", "♥")), content["rules"]
        )
    )
    return f'''<div class="wrap">
  <section class="hero">
    <div class="hero-copy">
      <p class="genre">{esc(copy["genre"])}</p>
      <h1 class="wordmark">{esc(copy["brand"])}</h1>
      <p class="tagline">{esc(content["tagline"])}</p>
      <p class="hero-desc">{esc(content["description"])}</p>
      <a class="primary" href="{route(lang, "play")}">{esc(copy["nav"]["play"])}</a>
    </div>
    <div class="hero-art" aria-hidden="true">{board()}</div>
  </section>
  <section class="rules">
    <h2>{esc(content["rules_title"])}</h2>
    <ul class="rule-grid">{rules}</ul>
  </section>
  <section class="launch">
    <div>
      <h2>{esc(content["launch_title"])}</h2>
      <p>{esc(content["launch_body"])}</p>
    </div>
    {store_status(copy)}
  </section>
</div>'''


def store_status(copy):
    status = esc(copy["coming"])
    return f'''<div class="stores">
      <div><strong>App Store</strong><span>{status}</span></div>
      <div><strong>Google Play</strong><span>{status}</span></div>
    </div>'''


def detail(title, description, body, kind=""):
    return f'''<article class="wrap document {kind}">
  <header class="document-header">
    <h1>{esc(title)}</h1>
    <p>{esc(description)}</p>
  </header>
  {body}
</article>'''


def play(copy):
    content = copy["play"]
    return detail(
        copy["nav"]["play"], content["description"],
        f'''<div class="preview">
  {board()}
  <div class="preview-copy"><h2>{esc(copy["coming"])}</h2><p>{esc(content["body"])}</p></div>
</div>
{store_status(copy)}''', "play"
    )


def policy(copy, page):
    content = copy[page]
    sections = "".join(
        f'<section><h2>{esc(title)}</h2><p>{esc(body)}</p></section>'
        for title, body in content["sections"]
    )
    if page == "privacy":
        sections += (
            '<p class="provider-links"><a href="https://www.apple.com/legal/privacy/">Apple</a>'
            '<a href="https://policies.google.com/privacy">Google</a></p>'
        )
    sections += (
        f'<section><h2>{esc(copy["contact"])}</h2>'
        f'<p><a href="mailto:{CONTACT}">{CONTACT}</a></p></section>'
    )
    return detail(copy["nav"][page], content["description"], '<div class="prose">' + sections + '</div>')


def post_editions(slug, post):
    return {
        lang: {**edition, "url": BASE + route(lang, "journal/" + slug)}
        for lang, edition in post["editions"].items()
    }


def journal_index(lang, copy, posts):
    title = copy["nav"]["journal"]
    description = copy["journal"]["description"]
    cards = "".join(
        f'<li><a href="{route(lang, "journal/" + slug)}"><h2>{esc(post["editions"][lang]["title"])}</h2>'
        f'<p>{esc(post["editions"][lang]["summary"])}</p></a></li>'
        for slug, post in posts.items()
    )
    body = '<ul class="post-list">' + cards + '</ul>' if cards else (
        f'<p class="journal-empty">{esc(copy["journal"]["empty"])}</p>'
    )
    return detail(title, description, body)


def journal_post(lang, post, asset_urls):
    edition = post["editions"][lang]
    prose = "".join(f'<p>{esc(paragraph)}</p>' for paragraph in edition["body"])
    figure = f'<figure><img src="{esc(asset_urls[post["image"]])}" alt="{esc(edition["alt"])}"></figure>'
    return detail(edition["title"], edition["summary"], '<div class="prose">' + figure + prose + '</div>')


def render(lang, page, copy, title, description, body, asset_urls, structured=None):
    urls = variants(page)
    headline = title if not page else f'{title} · {copy["brand"]}'
    entry = " data-language-entry" if lang == languages.DEFAULT else ""
    alternates = seo.alternate_links(urls, urls[languages.DEFAULT])
    metadata = f"  {seo.jsonld_script(structured)}\n" if structured else ""
    stylesheet = esc(asset_urls["shoopa.css"])
    scripts = [
        langswitch.script({"js": asset_urls["ipe-lang.js"]}),
        f'<script src="{esc(asset_urls["language.js"])}" defer></script>',
    ]
    return f'''<!doctype html>
<html lang="{lang}"{entry}>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{esc(seo.meta_desc(description))}">
  <meta name="theme-color" content="#f5f7fc">
  <meta property="og:type" content="{'article' if structured else 'website'}">
  <meta property="og:title" content="{esc(headline)}">
  <meta property="og:description" content="{esc(seo.meta_desc(description))}">
  <meta property="og:url" content="{urls[lang]}">
  <title>{esc(headline)}</title>
  <link rel="canonical" href="{urls[lang]}">
  {alternates}
  <link rel="icon" type="image/png" href="{esc(asset_urls["icon.png"])}">
  <link rel="stylesheet" href="{stylesheet}">
{metadata}  {"".join(scripts)}
</head>
<body>
  {header(lang, page, copy)}
  <main>{body}</main>
  {footer(lang, page, copy)}
</body>
</html>
'''


def expected_files():
    copies = {lang: read_json(ROOT / "content" / f"{lang}.json") for lang in languages.SUPPORTED}
    posts = {path.stem: read_json(path) for path in sorted((ROOT / "content/journal").glob("*.json"))}
    editions = {slug: post_editions(slug, post) for slug, post in posts.items()}
    published = {slug: posts[slug] for slug in journal.publishable(editions)}
    loaded_assets = {
        name: (ROOT / "assets" / name).read_bytes()
        for name in ("language.js", "icon.png", "jua-logo.woff", "Jua-OFL.txt")
    }
    loaded_assets["ipe-lang.js"] = (ASSETS / "ipe-lang.js").read_bytes()
    loaded_assets["shoopa.css"] = (ROOT / "assets/shoopa.css").read_text(encoding="utf-8").replace(
        "jua-logo.woff", f'jua-logo.woff?v={hashlib.sha256(loaded_assets["jua-logo.woff"]).hexdigest()[:12]}'
    ).encode("utf-8")
    for post in published.values():
        image = post["image"]
        loaded_assets[image] = (ROOT / "assets" / image).read_bytes()
    files = {f"assets/{name}": data for name, data in loaded_assets.items()}
    asset_urls = {
        name: f"/assets/{name}?v={hashlib.sha256(data).hexdigest()[:12]}"
        for name, data in loaded_assets.items()
    }

    for lang, copy in copies.items():
        pages = {
            "": (f'{copy["brand"]} · {copy["genre"]}', copy["home"]["description"], home(lang, copy)),
            "play": (copy["nav"]["play"], copy["play"]["description"], play(copy)),
            "privacy": (copy["nav"]["privacy"], copy["privacy"]["description"], policy(copy, "privacy")),
            "terms": (copy["nav"]["terms"], copy["terms"]["description"], policy(copy, "terms")),
            "journal": (copy["nav"]["journal"], copy["journal"]["description"], journal_index(lang, copy, published)),
        }
        for page, (title, description, body) in pages.items():
            files[route(lang, page)[1:] + "index.html"] = render(
                lang, page, copy, title, description, body, asset_urls
            ).encode()
        for slug, post in published.items():
            page = "journal/" + slug
            edition = post["editions"][lang]
            structured = journal.blogposting(
                editions[slug], lang, description=edition["summary"],
                publisher=seo.org_ref(), image=BASE + asset_urls[post["image"]],
            )
            files[route(lang, page)[1:] + "index.html"] = render(
                lang, page, copy, edition["title"], edition["summary"],
                journal_post(lang, post, asset_urls), asset_urls, structured,
            ).encode()

    sitemap_entries = [
        journal.sitemap_entry({lang: {"url": url} for lang, url in variants(page).items()})
        for page in PAGES
    ] + [journal.sitemap_entry(editions[slug]) for slug in published]
    files["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(sitemap_entries) + "\n</urlset>\n"
    ).encode()
    files["robots.txt"] = f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n".encode()
    files["CNAME"] = f"{DOMAIN}\n".encode()
    files[".nojekyll"] = b""
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = expected_files()
    stale = {
        path.relative_to(PUBLIC).as_posix()
        for path in PUBLIC.rglob("*") if path.is_file()
    } - files.keys()
    if args.check:
        for name, data in files.items():
            path = PUBLIC / name
            if not path.is_file() or path.read_bytes() != data:
                stale.add(name)
        for name in sorted(stale):
            print(f"생성물 불일치 {name}", file=sys.stderr)
        if stale:
            return 1
    else:
        for name, data in files.items():
            path = PUBLIC / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for name in stale:
            (PUBLIC / name).unlink()
    print(f"공개 파일 {len(files)}개 {'검증' if args.check else '생성'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
