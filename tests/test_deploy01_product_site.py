"""DEPLOY-01 public website build contract, exercised as an operator command."""
import os
from pathlib import Path
import subprocess
import sys
from html.parser import HTMLParser

import pytest

ROOT = Path(__file__).resolve().parents[1]


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}
        self.href = None
        self.texts = []
        self.h1 = 0
        self.scripts = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a": self.href = attrs.get("href")
        if tag == "h1": self.h1 += 1
        if tag == "script": self.scripts += 1
    def handle_endtag(self, tag):
        if tag == "a": self.href = None
    def handle_data(self, data):
        self.texts.append(data)
        if self.href is not None and data.strip(): self.links[data.strip()] = self.href


def build(tmp_path, value):
    env = dict(os.environ)
    env.pop("PRODUCT_APP_URL", None)
    if value is not None: env["PRODUCT_APP_URL"] = value
    out = tmp_path / "public"
    result = subprocess.run([sys.executable, "scripts/build_product_site.py", "--output", str(out)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)
    return result, out


@pytest.mark.parametrize("value", [None, "", "http://app.example", "https://user:password@app.example", "https://app.example/login", "https://app.example?x=1", "https://app.example#fragment", "javascript:alert(1)", "https://", "//app.example"])
def test_deploy01_ac7_invalid_app_origin_fails_before_publish(tmp_path, value):
    result, out = build(tmp_path, value)
    assert result.returncode != 0
    assert "PRODUCT_APP_URL must be an HTTPS origin." in result.stdout + result.stderr
    assert not (out / "index.html").exists()


@pytest.mark.parametrize("value", ["https://learnswe.example", "  https://learnswe.example/  "])
def test_deploy01_ac7_8_build_links_copy_and_subpath_assets(tmp_path, value):
    result, out = build(tmp_path, value)
    assert result.returncode == 0, result.stderr
    html = (out / "index.html").read_text(encoding="utf-8")
    doc = Document(); doc.feed(html)
    assert doc.links["Open learnSWE"] == "https://learnswe.example/login"
    assert doc.links["Skip to content"] == "#main"
    assert doc.links["How it works"] == "#how-it-works"
    assert doc.links["View source"] == "https://github.com/CS3227-2610-MP4-learnSWE/CS3227-2610-MP4"
    assert doc.h1 == 1
    assert doc.scripts == 0
    assert "__APP_LOGIN_URL__" not in html
    assert "Learn software engineering. Build understanding." in html
    assert "AI features require the configured SoC LLM service. Teachers review generated learning content before publication." in html
    for label in ["Students", "Teachers", "Administrators", "Built for every role"]:
        assert label in html
    assert (out / ".nojekyll").exists()
    assert (out / "styles.css").exists()
    assert 'href="/styles.css"' not in html
    assert "SOCLAAS_API_KEY" not in html
    assert "DATABASE_URL" not in html
