"""Exercise the offline review and capture desktop/mobile views.

SPDX-License-Identifier: CC-BY-SA-4.0
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT=Path(__file__).resolve().parents[1]/"out"


def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1100},device_scale_factor=1)
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto((OUT/"review.html").as_uri())
        page.locator("#verdict[data-pass=true]").wait_for()
        page.screenshot(path=str(OUT/"preview.png"),full_page=True)
        page.locator(".hero").screenshot(path=str(OUT/"model.png"))
        page.locator("#mmc").click();assert page.locator("#verdict").get_attribute("data-pass")=="false"
        mmc=page.evaluate("window.inspectionResult")
        page.locator("#bonus").click();assert page.locator("#verdict").get_attribute("data-pass")=="true"
        bonus=page.evaluate("window.inspectionResult")
        assert abs(bonus["actual"]-2*(.12**2+.06**2)**.5)<1e-12
        assert abs(bonus["gap"]-((8.5-8.2)/2-(.12**2+.06**2)**.5))<1e-12
        page.locator("#tilted").click();assert page.locator("#verdict").get_attribute("data-pass")=="false"
        tilted=page.evaluate("window.inspectionResult")
        page.locator("#variant").click();assert "18 mm flange" in page.locator("#modelstate").inner_text()
        assert page.locator("#stepfile").get_attribute("href")=="flange.t18.step"
        page.locator("#datums").click();page.screenshot(path=str(OUT/"qa-datums.png"),full_page=True)
        page.locator("#top").click();page.screenshot(path=str(OUT/"qa-plan.png"),full_page=True)
        page.locator("#iso").click();page.locator("#variant").click();page.locator("#datums").click();page.locator("#bonus").click()
        before=page.locator("canvas").screenshot()
        box=page.locator("canvas").bounding_box();page.mouse.move(box['x']+200,box['y']+240);page.mouse.down();page.mouse.move(box['x']+280,box['y']+260);page.mouse.up()
        assert before!=page.locator("canvas").screenshot(),"orbit did not change rendering"
        page.locator("#iso").click()
        page.set_viewport_size({"width":390,"height":844})
        page.screenshot(path=str(OUT/"qa-mobile.png"),full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"),"mobile overflow"
        assert not errors,errors
        result=dict(javascript_errors=errors,mmc=mmc,bonus=bonus,tilted=tilted,
                    variant_link=True,orbit_changes_pixels=True,mobile_overflow=False)
        (OUT/"browser-evidence.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result,indent=2));browser.close()


if __name__=="__main__":
    main()
