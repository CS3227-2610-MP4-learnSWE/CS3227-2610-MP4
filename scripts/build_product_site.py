"""Build the public site without exposing application secrets."""
import argparse
import html
import os
from pathlib import Path
import shutil
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> None:
    origin = os.environ.get('PRODUCT_APP_URL', '').strip()
    try:
        url = urlsplit(origin)
        valid = (url.scheme == 'https' and bool(url.hostname) and url.username is None
                 and url.password is None and url.path in ('', '/') and not url.query
                 and not url.fragment and not any(c.isspace() for c in origin)
                 and url.port != 0 and not any(c in origin for c in '?#\\<>\"\'')
                 and bool(re.fullmatch(r'[a-zA-Z0-9.:-]+', url.hostname)))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('PRODUCT_APP_URL must be an HTTPS origin.')
    template = (ROOT / 'website/index.html').read_text(encoding='utf-8')
    if template.count('__APP_LOGIN_URL__') != 1:
        raise ValueError('Product website must contain exactly one application link token.')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(template.replace('__APP_LOGIN_URL__',
        html.escape(origin.rstrip('/') + '/login', quote=True)), encoding='utf-8')
    shutil.copyfile(ROOT / 'website/styles.css', output / 'styles.css')
    (output / '.nojekyll').touch()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/product-site')
    args = parser.parse_args()
    try:
        build(args.output)
    except ValueError as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
