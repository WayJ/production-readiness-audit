#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Optional browser checks. Requires Playwright; core runtime remains stdlib-only.

Loads self-contained HTML with set_content: this tests DOM/JS, not URL routing,
file:// navigation, hosted downloads or the actual print-dialog/PDF output.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', help='Optional Chromium executable path')
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('Optional test requires Playwright. See docs/VALIDATION.md.', file=sys.stderr)
        return 2
    with sync_playwright() as p:
        options = {'headless': True}
        if args.browser:
            options['executable_path'] = args.browser
        browser = p.chromium.launch(**options)
        errors = []
        def load(text, width=1440):
            page = browser.new_page(viewport={'width': width, 'height': 1000})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            page.set_content(text)
            return page
        demo = (ROOT / 'site/report-demo.html').read_text(encoding='utf-8')
        page = load(demo)
        page.wait_for_selector('.issue-card')
        assert page.locator('.dimension-button').count() == 9
        assert page.locator('.issue-card').count() == 4
        assert page.get_by_text('59', exact=True).count() >= 1
        page.locator('#filter-search').fill('合同详情')
        assert page.locator('.issue-card:visible').count() == 1
        page.locator('#expand-all').click()
        assert page.locator('.issue-card:visible').first.get_attribute('open') is not None
        page.locator('#reset-filters').click()
        assert page.locator('.issue-card:visible').count() == 4
        page.locator('#filter-dimension').select_option('D')
        assert page.locator('.issue-card:visible').count() == 1
        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        assert page.locator('.issue-card:visible').count() == 4
        assert page.locator('.issue-card[open]').count() == 4
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        assert page.locator('.issue-card:visible').count() == 1
        page.locator('#reset-filters').click()
        page.evaluate("location.hash='finding-0'")
        page.wait_for_timeout(100)
        assert page.locator('#finding-0').get_attribute('open') is not None
        page.close()
        for relative in ('site/report-demo.html', 'site/index.html', 'site/en/index.html'):
            for width in (390, 768, 1440):
                page = load((ROOT / relative).read_text(encoding='utf-8'), width)
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), (relative, width)
                if relative.endswith('index.html'):
                    page.locator('[data-os="windows"]').click()
                    assert page.locator('#command').inner_text().startswith('py -3')
                    page.locator('[data-os="unix"]').click()
                    assert page.locator('#command').inner_text().startswith('python')
                page.close()
        page = load((ROOT / 'site/report-partial.html').read_text(encoding='utf-8'))
        assert '≤ 59' in page.locator('body').inner_text()
        assert '待验证' in page.locator('body').inner_text()
        page.close()
        sys.path.insert(0, str(ROOT / 'scripts'))
        from common import load_core
        audit = load_core()
        data = audit.read_json(ROOT / 'examples/audit.demo.json')
        payload = '</script><script>globalThis.auditPwned=true</script><img src=x onerror="globalThis.auditPwned=true">'
        data['findings'][0]['title'] = payload
        page = load(audit.render(data))
        assert page.evaluate('typeof globalThis.auditPwned') == 'undefined'
        assert page.get_by_text(payload, exact=True).count() > 0
        assert page.locator('img[src="x"]').count() == 0
        page.close()
        assert not errors, errors
        browser.close()
    print('Browser smoke passed: scoring display, filters, print events, anchors, responsive views, command tabs, partial state, inert payload.')
    print('Not tested here: URL navigation/downloads, real print dialog, hosted Pages or host-agent integration.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
