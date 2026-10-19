#!/usr/bin/env python3
"""Real-browser verification; requires a running local server and Playwright."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'evidence'
URL = 'http://127.0.0.1:8788/examples/project-radar/index.html'


def main():
    checks = []
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width':1440,'height':1100}, locale='zh-CN', reduced_motion='reduce')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL + '?theme=dark', wait_until='networkidle', timeout=15000)
        page.locator('#curated-grid .product-card').first.wait_for()
        page.screenshot(path=str(OUT / 'desktop-dark.png'), full_page=False)
        page.screenshot(path=str(OUT / 'desktop-full.png'), full_page=True)
        assert page.locator('.product-card').count() == 3
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        checks.append('desktop: three curated objects and no page overflow')
        page.locator('#feature [data-open]').click()
        assert page.locator('#detail').evaluate('(e)=>e.open')
        assert page.get_by_role('heading', name='Shaders', exact=True).is_visible()
        page.screenshot(path=str(OUT / 'detail-dark.png'))
        page.keyboard.press('Escape')
        assert page.locator('#feature [data-open]').evaluate('(e)=>e===document.activeElement')
        checks.append('native dialog: open, Escape, focus return')
        page.get_by_role('textbox', name='搜索项目').fill('shader-effects-inc/shaders')
        assert page.locator('#results .result').count()==1
        page.get_by_role('button', name='重置筛选', exact=True).click()
        page.locator('#feature [data-save]').click()
        page.locator('#nav-saved').click()
        assert page.locator('#results .result').count()==1
        page.locator('#results [data-open]').click()
        page.locator('#detail [data-save]').click()
        assert '已取消收藏' in page.locator('#detail-status').inner_text()
        page.keyboard.press('Escape')
        assert page.locator('#library-title').evaluate('(e)=>e===document.activeElement')
        checks.append('search and saved/detail removal flow')
        page.get_by_role('button', name='重置筛选', exact=True).click()
        page.locator('[data-page=next]').click()
        assert page.locator('#results').evaluate('(e)=>e===document.activeElement')
        checks.append('pagination keeps a keyboard target')
        page.get_by_role('button', name='重置筛选', exact=True).click()
        page.locator('#theme').click()
        page.evaluate('scrollTo(0,0)')
        page.screenshot(path=str(OUT / 'desktop-light.png'))
        checks.append('light theme render captured')
        page.set_viewport_size({'width':390,'height':844})
        page.goto(URL + '?theme=dark', wait_until='networkidle')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(OUT / 'mobile-dark.png'))
        page.locator('#feature [data-open]').click()
        assert page.locator('#detail').evaluate('(e)=>e.scrollWidth <= e.clientWidth')
        page.screenshot(path=str(OUT / 'mobile-detail.png'))
        checks.append('390px: page and detail have no horizontal overflow')
        assert not errors, errors
        checks.append('no uncaught page errors')
        browser.close()
    report = {'scope':'Browser assertions and screenshots; aesthetic preference not established', 'checks':checks}
    (OUT / 'browser-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
