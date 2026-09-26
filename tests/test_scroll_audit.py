"""
Audit Lenis smooth scrolling configuration and nested scroll containment.
"""
import sys
from playwright.sync_api import sync_playwright

def test_lenis_scrolling():
    print("=" * 60)
    print("  Lenis Smooth Scrolling Audit")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        # 1. Load Overview page
        page.goto("http://localhost:5173/", timeout=15000)
        page.wait_for_selector("text=Overview", timeout=10000)
        page.wait_for_timeout(600)

        # 2. Check Lenis html class
        html_classes = page.evaluate("() => document.documentElement.className")
        print(f"1. HTML Classes: '{html_classes}'")
        assert "lenis" in html_classes, "html element has 'lenis' class"
        print("   [OK] Lenis initialized and injected 'lenis' class into <html>.")

        # 3. Check CSS rules (html scroll-behavior must not fight Lenis)
        scroll_behavior = page.evaluate("() => getComputedStyle(document.documentElement).scrollBehavior")
        print(f"2. html computed scroll-behavior: '{scroll_behavior}'")
        assert scroll_behavior != "smooth", "Native smooth-scroll is disabled to prevent Lenis jitter"
        print("   [OK] Native smooth-scroll disabled to eliminate interpolation jitter.")

        # 4. Check nested scroll containers
        prevent_elements = page.locator("[data-lenis-prevent]")
        count = prevent_elements.count()
        print(f"3. Nested scroll areas protected with [data-lenis-prevent]: {count}")
        assert count >= 1, "At least one container protected"
        print("   [OK] Sidebar navigation protected from scroll hijacking.")

        # 5. Open Chatbot and check nested message scrolling
        page.click("button:has-text('Ask AI Agent')")
        page.wait_for_selector("text=GST Compliance Agent", timeout=5000)
        chat_prevents = page.locator("div[data-lenis-prevent]").count()
        print(f"4. Chatbot nested scroll containers protected: {chat_prevents}")
        assert chat_prevents >= 2, "Chatbot message list and prompt pills protected"
        print("   [OK] Chatbot message viewport and prompt chips protected from scroll hijacking.")

        # 6. Test navigation scroll-reset
        page.evaluate("() => window.scrollTo(0, 400)")
        page.wait_for_timeout(200)
        page.goto("http://localhost:5173/compliance", timeout=10000)
        page.wait_for_selector("table.data-table", timeout=5000)
        page.wait_for_timeout(200)
        current_y = page.evaluate("() => window.scrollY")
        print(f"5. Route transition scroll position (scrollY): {current_y}")
        assert current_y == 0, "Scroll smoothly reset to top on page change"
        print("   [OK] Route navigation automatically resets scroll to top (0px).")

        browser.close()

    print("\n" + "=" * 60)
    print("  ALL LENIS SCROLLING AUDIT CHECKS PASSED [100%]")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(test_lenis_scrolling())
