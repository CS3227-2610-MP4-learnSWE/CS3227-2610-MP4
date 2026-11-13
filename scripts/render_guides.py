"""Render repository documentation as self-contained product website pages."""
import html
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

REPOSITORY = "https://github.com/CS3227-2610-MP4-learnSWE/CS3227-2610-MP4/blob/master/"
PAGES = {
    "docs/UserGuide.md": ("user-guide.html", "User guide", "Learn, practise and manage your workspace.", "For students, teachers & administrators"),
    "docs/DeveloperGuide.md": ("developer-guide.html", "Developer guide", "Build, configure and maintain learnSWE.", "For developers & maintainers"),
    "README.md": ("getting-started.html", "Getting started", "Set up your local learning environment.", "Setup & troubleshooting"),
    "docs/SharedDataContract.md": ("data-contract.html", "Shared data contract", "The shared application data model.", "Technical reference"),
}


def navigation(current):
    links = []
    for filename, title in [("index.html", "Overview"), ("user-guide.html", "User guide"), ("developer-guide.html", "Developer guide")]:
        active = ' aria-current="page"' if filename == current else ''
        links.append(f'<a href="./{filename}"{active}>{title}</a>')
    return '<nav class="site-tabs" aria-label="Main navigation">' + ''.join(links) + '</nav>'


def render_guides(root: Path, output: Path):
    parser = MarkdownIt("commonmark", {"html": False}).enable("table")
    for source, (filename, title, description, audience) in PAGES.items():
        text = (root / source).read_text(encoding="utf-8")
        # Replace the duplicate Markdown contents with the page's generated navigation.
        text = re.sub(r"(?ms)^## Contents\n.*?(?=^## )", "", text)
        tokens = parser.parse(text)
        headings = []
        seen = {}
        for index, token in enumerate(tokens):
            if token.type == "heading_open":
                label = tokens[index + 1].content
                slug = re.sub(r"[^\w -]", "", label.lower()).replace(" ", "-")
                count = seen.get(slug, 0)
                seen[slug] = count + 1
                anchor = slug + (f"-{count}" if count else "")
                token.attrSet("id", anchor)
                if token.tag == "h2":
                    headings.append(f'<a href="#{anchor}">{html.escape(label)}</a>')
            for child in token.children or []:
                if child.type not in ("link_open", "image"):
                    continue
                attr = "src" if child.type == "image" else "href"
                target = child.attrGet(attr) or ""
                if urlsplit(target).scheme or target.startswith(("#", "//")):
                    continue
                path, separator, fragment = target.partition("#")
                resolved = (root / source).parent.joinpath(path).resolve()
                relative = resolved.relative_to(root.resolve()).as_posix()
                if relative in PAGES:
                    target = './' + PAGES[relative][0]
                elif relative.startswith("docs/images/guide/"):
                    target = './images/guide/' + relative.removeprefix("docs/images/guide/")
                elif relative.startswith("docs/sample-files/"):
                    target = './sample-files/' + relative.removeprefix("docs/sample-files/")
                else:
                    target = REPOSITORY + relative
                child.attrSet(attr, target + (separator + fragment if separator else ""))
                if child.type == "image":
                    child.attrSet("loading", "lazy")
                    child.attrSet("decoding", "async")
        body = parser.renderer.render(tokens, parser.options, {})
        body = re.sub(r'<h1[^>]*>.*?</h1>\n?', '', body, count=1, flags=re.S)
        body = body.replace('<table>', '<div class="table-scroll" tabindex="0" role="region" aria-label="Guide table"><table>').replace('</table>', '</table></div>')
        page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{description}"><title>{title} | learnSWE</title>
<link rel="stylesheet" href="./styles.css"><link rel="stylesheet" href="./guide.css"></head>
<body class="guide-page"><a class="skip" href="#main">Skip to content</a>
<header class="wrap"><a class="brand" href="./index.html" aria-label="learnSWE home">learnSWE<span class="dot" aria-hidden="true">.</span></a><span class="header-note">Documentation</span></header>
<div class="wrap">{navigation(filename)}</div>
<main id="main" class="wrap guide-layout" tabindex="-1">
<aside class="guide-sidebar"><details open><summary>On this page</summary><nav aria-label="On this page">{''.join(headings)}</nav></details></aside>
<div class="guide-main"><div class="guide-intro"><p class="eyebrow">{audience}</p><h1>{title}</h1><p class="lead">{description}</p><div class="guide-meta"><span>learnSWE documentation</span><span>Always in step with the project</span></div></div>
<article class="guide-content">{body}</article>
<div class="guide-end"><span>You're at the end of the guide.</span><a href="#main">Back to top &uarr;</a></div></div></main>
<footer class="wrap"><p>learnSWE &middot; A CS3227 software engineering project.</p><a href="./index.html">Back to overview</a></footer></body></html>'''
        (output / filename).write_text(page, encoding="utf-8")
    shutil.copytree(root / "docs/images/guide", output / "images/guide", dirs_exist_ok=True)
    shutil.copytree(root / "docs/sample-files", output / "sample-files", dirs_exist_ok=True)
    shutil.copyfile(root / "website/guide.css", output / "guide.css")
