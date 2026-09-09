"""Render and exercise the local motion page using headless Playwright.

Optional presentation QA; requires playwright and its Chromium browser.
SPDX-License-Identifier: CC-BY-SA-4.0
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "out"


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width":1440, "height":1050}, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto((OUT / "motion.html").as_uri())
        page.get_by_role("button", name="Play", exact=True).wait_for()
        for index in (0,30,40,60):
            page.locator("#pose").fill(str(index))
            assert page.locator("#drawing").get_attribute("data-pose") == str(index)
            assert f"Pose {index+1} / 61" in page.locator("#caption").inner_text()
            page.screenshot(path=str(OUT / ("preview.png" if index==40 else f"qa-pose-{index}.png")),full_page=True)
        page.get_by_role("button",name="Play",exact=True).click()
        page.wait_for_function("document.getElementById('drawing').dataset.pose !== '60'")
        page.get_by_role("button",name="Pause",exact=True).click()
        page.set_viewport_size({"width":390,"height":844})
        page.locator("#pose").fill("40")
        page.screenshot(path=str(OUT / "qa-mobile.png"),full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "mobile overflow"
        assert not errors, errors
        result = dict(javascript_errors=errors, tested_poses=[0,30,40,60],
                      playback_verified=True, mobile_overflow=False)
        (OUT / "preview-evidence.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result))
        browser.close()


if __name__ == "__main__":
    main()
