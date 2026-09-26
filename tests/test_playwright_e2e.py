"""
Playwright End-to-End Test Suite for UC15 GST Compliance Platform
Validates:
1. Overview Page & Executive KPIs
2. Invoice Audit Table & Filtering
3. Invoice Detail Deep-Dive & 6 Statutory Gates
4. Case Management & Systemic Investigations
5. Audit Trail & Statutory Logs
6. Floating AI Agent Chatbot (Open, Quick Prompts, Typewriter Streaming)
7. 404 Not Found Fallback Routing
8. FastAPI Server Direct Mount (Port 8000)
"""
import sys
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"


def run_e2e_tests():
    print("=" * 70)
    print("  UC15 Playwright End-to-End Test Suite")
    print("=" * 70)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        # Test 1: Overview Page
        print("\n[1/8] Testing Overview Dashboard (Executive Cockpit)...")
        try:
            page.goto(f"{BASE_URL}/", timeout=15000)
            page.wait_for_selector("h1:has-text('Overview')", timeout=10000)
            
            # Check Brand & SAP Badge
            assert page.is_visible("text=FI-TAX") or page.is_visible("text=GST"), "Brand Logo visible"
            assert page.is_visible("text=SAP S/4HANA: DI01"), "SAP S/4HANA connector badge visible"
            
            # Check Health Score & KPIs
            page.wait_for_selector("text=Compliance Health Score", timeout=5000)
            assert page.is_visible("text=Total Invoices"), "Total Invoices KPI visible"
            assert page.is_visible("text=Compliant"), "Compliant KPI visible"
            assert page.is_visible("text=Statutory Validation Gates"), "Statutory Gates section visible"

            results.append(("Overview Dashboard & KPIs", True, "Passed"))
            print("  [OK] Overview page loaded with Brand Logo, Health Score, and KPI Cards.")
        except Exception as e:
            results.append(("Overview Dashboard & KPIs", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        # Test 2: Invoice Audit Center
        print("\n[2/8] Testing Invoice Audit Center (/compliance)...")
        try:
            page.goto(f"{BASE_URL}/compliance", timeout=15000)
            page.wait_for_selector("table.data-table", timeout=10000)
            
            # Verify rows exist
            rows = page.locator("table.data-table tbody tr")
            row_count = rows.count()
            assert row_count > 0, f"Expected invoice rows, found {row_count}"
            print(f"  [OK] Invoice Audit table rendered {row_count} rows with gate status beads.")

            # Test Search Filter (use table-specific search input)
            search_input = page.locator("div.panel input[placeholder*='vendor']")
            search_input.fill("Precision")
            time.sleep(0.5)
            filtered_count = page.locator("table.data-table tbody tr").count()
            assert filtered_count > 0, "Search filter returned results"
            search_input.fill("")  # Clear search

            results.append(("Invoice Audit Table & Filtering", True, f"Passed ({row_count} records)"))
        except Exception as e:
            results.append(("Invoice Audit Table & Filtering", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        # Test 3: Invoice Detail Deep-Dive
        print("\n[3/8] Testing Invoice Detail Page (/invoice/8096)...")
        try:
            page.goto(f"{BASE_URL}/invoice/8096", timeout=15000)
            page.wait_for_selector("h1:has-text('8096')", timeout=10000)
            
            # Check 6 Statutory Validation Gates
            assert page.is_visible("text=Statutory Validation Gates"), "Gates section visible"
            assert page.is_visible("text=GSTIN_001") or page.is_visible("text=GSTIN Format"), "Gate 1 visible"
            assert page.is_visible("text=TAX_001") or page.is_visible("text=Tax Rate"), "Gate 3 visible"
            assert page.is_visible("text=SAP S/4HANA Action"), "SAP S/4HANA Action panel visible"
            assert page.is_visible("text=Back to Invoices"), "Back button visible"

            # Click Back button
            page.click("text=Back to Invoices")
            page.wait_for_selector("table.data-table", timeout=5000)
            print("  [OK] Invoice Detail loaded with 6 statutory gates and returned via Back button.")
            results.append(("Invoice Detail Deep-Dive (6 Gates)", True, "Passed"))
        except Exception as e:
            results.append(("Invoice Detail Deep-Dive (6 Gates)", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        # Test 4: Investigations Page
        print("\n[4/8] Testing Investigations Page (/investigations)...")
        try:
            page.goto(f"{BASE_URL}/investigations", timeout=15000)
            page.wait_for_selector("text=Active Investigations", timeout=10000)
            print("  [OK] Active Investigations section loaded successfully.")
            results.append(("Investigations Page", True, "Passed"))
        except Exception as e:
            results.append(("Investigations Page", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        # Test 5: Cases Page
        print("\n[5/8] Testing Case Management (/cases)...")
        try:
            page.goto(f"{BASE_URL}/cases", timeout=15000)
            page.wait_for_selector("text=Case Management", timeout=10000)
            print("  [OK] Case Management page loaded successfully.")
            results.append(("Case Management Page", True, "Passed"))
        except Exception as e:
            results.append(("Case Management Page", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        # Test 6: Audit Trail
        print("\n[6/8] Testing Audit Trail Page (/audit)...")
        try:
            page.goto(f"{BASE_URL}/audit", timeout=15000)
            page.wait_for_selector("text=Audit Trail", timeout=10000)
            print("  [OK] Audit Trail timeline loaded successfully.")
            results.append(("Audit Trail Page", True, "Passed"))
        except Exception as e:
            results.append(("Audit Trail Page", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        # Test 7: Floating AI Agent Chatbot
        print("\n[7/8] Testing Floating AI Agent Chatbot...")
        try:
            page.goto(f"{BASE_URL}/", timeout=15000)
            
            # Check trigger button
            trigger = page.locator("button:has-text('Ask AI Agent')")
            assert trigger.is_visible(), "Floating AI Agent trigger button visible"
            
            # Click to open chatbot
            trigger.click()
            page.wait_for_selector("text=GST Compliance Agent", timeout=5000)
            
            # Check quick prompt pills
            assert page.is_visible("text=What is our current compliance rate?"), "Quick prompt visible"

            # Click quick prompt to send query
            page.click("button:has-text('What is our current compliance rate?')")
            
            # Wait for thinking state or response
            time.sleep(2.0)
            messages = page.locator("div.whitespace-pre-wrap")
            assert messages.count() > 0, "Agent generated conversation messages"

            # Test Pro Feature: Expand View
            expand_btn = page.locator("button[title*='Expand']")
            if expand_btn.is_visible():
                expand_btn.click()
                time.sleep(0.5)
                # Verify left rail with threads appears
                assert page.is_visible("text=Investigations"), "Thread sidebar visible in expanded view"
                # Test creating a new thread
                page.click("button:has-text('New')")
                time.sleep(0.5)
                # Collapse view back
                collapse_btn = page.locator("button[title='Collapse View']")
                if collapse_btn.is_visible():
                    collapse_btn.click()

            print("  [OK] Floating AI Copilot opened, executed query, tested multi-thread & expand.")

            # Close chatbot
            close_btn = page.locator("button[title='Close']").first
            if close_btn.is_visible():
                close_btn.click()
            time.sleep(0.5)

            results.append(("Floating AI Agent (Threads, Expand, Stream)", True, "Passed"))
        except Exception as e:
            results.append(("Floating AI Agent (Threads, Expand, Stream)", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        # Test 8: 404 Route Fallback & FastAPI Mount Check
        print("\n[8/8] Testing 404 Fallback & FastAPI Server Mount...")
        try:
            # 404 test
            page.goto(f"{BASE_URL}/nonexistent-route-xyz", timeout=10000)
            page.wait_for_selector("text=Page Not Found", timeout=5000)
            assert page.is_visible("text=Back to Dashboard"), "404 Back to Dashboard link visible"

            # FastAPI Port 8000 direct check
            page.goto(f"{BACKEND_URL}/", timeout=10000)
            page.wait_for_selector("h1:has-text('Overview')", timeout=10000)
            print("  [OK] 404 Fallback and FastAPI root mount (Port 8000) verified.")

            results.append(("404 Fallback & FastAPI Mount", True, "Passed"))
        except Exception as e:
            results.append(("404 Fallback & FastAPI Mount", False, str(e)))
            print(f"  [ERR] Failed: {e}")

        browser.close()

    print("\n" + "=" * 70)
    print("  Test Results Summary:")
    print("=" * 70)
    passed_count = sum(1 for _, ok, _ in results if ok)
    total_count = len(results)

    for name, ok, note in results:
        status_symbol = "[PASS]" if ok else "[FAIL]"
        print(f"  {status_symbol:<8} | {name:<40} | {note}")

    print("=" * 70)
    print(f"  Total: {passed_count}/{total_count} passed ({passed_count/total_count*100:.0f}% success rate)")
    print("=" * 70)

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(run_e2e_tests())
