import time
from playwright.sync_api import sync_playwright

def test_cases_and_investigations():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        # 1. Test Cases Page and Click
        print("Testing Case Management on http://localhost:5173/cases ...")
        page.goto("http://localhost:5173/cases", timeout=15000)
        page.wait_for_selector("text=Case Management", timeout=10000)
        time.sleep(1)

        rows = page.locator("div.panel .cursor-pointer")
        count = rows.count()
        print(f"Found {count} case rows.")
        assert count > 0, "Should have at least 1 case row"

        print("Clicking on the first case row...")
        rows.first.click()
        time.sleep(1)

        print(f"Current URL: {page.url}")
        assert "/cases/CASE-" in page.url, "URL should contain /cases/CASE-"

        # Wait for drawer to slide open
        page.wait_for_selector("text=Executive Statutory Finding", timeout=5000)
        print("  -> Executive Statutory Finding header is visible!")
        assert page.is_visible("text=Linked Enterprise Records"), "Linked Enterprise Records visible"
        assert page.is_visible("text=SAP S/4HANA FICO Controls"), "SAP Controls visible"
        assert page.is_visible("text=Submit Human Review"), "Human review section visible"
        assert page.is_visible("text=Approve Case"), "Approve Case button visible"
        assert page.is_visible("text=Reject Case"), "Reject Case button visible"
        assert page.is_visible("text=Apply Payment Block"), "Payment Block button visible"
        print("  -> Case Detail Drawer opened successfully with all statutory context, SAP controls, and action buttons!")

        # Close the drawer
        page.keyboard.press("Escape")
        # Or click backdrop or close button
        close_btn = page.locator("button:has-text('Approve Case')").locator("xpath=ancestor::div[contains(@class, 'w-screen')]").locator("button").first
        # Actually let's just click backdrop or navigate
        page.goto("http://localhost:5173/cases")
        time.sleep(0.5)

        # 2. Test Investigations Page and Click
        print("\nTesting Investigations on http://localhost:5173/investigations ...")
        page.goto("http://localhost:5173/investigations", timeout=15000)
        page.wait_for_selector("text=Active Investigations", timeout=10000)
        time.sleep(1)

        inv_rows = page.locator("div.panel .cursor-pointer")
        inv_count = inv_rows.count()
        print(f"Found {inv_count} investigation candidates.")
        assert inv_count > 0, "Should have at least 1 investigation candidate"

        print("Clicking on first investigation candidate...")
        inv_rows.first.click()
        time.sleep(1)

        print(f"Current Investigation URL: {page.url}")
        assert "/investigations/RC-" in page.url or "/investigations/INV-" in page.url, "URL should contain /investigations/..."

        page.wait_for_selector("text=Forensic Causality Hypothesis", timeout=5000)
        print("  -> Forensic Causality Hypothesis is visible!")
        assert page.is_visible("text=Forensic Multi-Dimensional Scorecard"), "Scorecard visible"
        assert page.is_visible("text=Systemic ERP Remediation"), "Remediation guidance visible"
        print("  -> Investigation Detail Drawer opened successfully with complete root-cause dossier!")

        browser.close()
        print("\n========================================================")
        print(" ALL INTERACTIVE CASE & INVESTIGATION CHECKS PASSED 100%!")
        print("========================================================")

if __name__ == "__main__":
    test_cases_and_investigations()
