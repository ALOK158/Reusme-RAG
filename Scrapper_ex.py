import os
import json
import argparse
import google.generativeai as genai
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from bs4 import BeautifulSoup # <- Import BeautifulSoup

# --- Configuration ---
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("🔴 GOOGLE_API_KEY not found in .env file. Please create it before running.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
CONFIG_FILE = 'config.json'

def get_selectors_from_gemini(html_content: str) -> dict:
    """
    Analyzes HTML with Gemini to extract CSS selectors for scraping.
    """
    print("🤖 Contacting Gemini to analyze website structure...")
    
    prompt = """
    You are an expert web scraping assistant. Analyze the provided HTML of a company's job listings page.
    Your task is to identify the CSS selectors for the following elements:

    1.  A container for each individual job posting (key: "job_item").
    2.  The job title within that job container (key: "title").
    3.  The job location within that job container (key: "location").
    4.  The link or button to click to go to the NEXT page of results (key: "pagination_next").

    You MUST return your response as a single, raw JSON object, and nothing else.
    Do not include markdown formatting like ```json or any explanations.
    Your response should look EXACTLY like this example:
    {
      "job_item": "div.job-card",
      "title": "h2.job-title",
      "location": "span.location",
      "pagination_next": "a.next-page"
    }
    """
    
    try:
        response = model.generate_content([prompt, html_content])
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        print("✅ Gemini analysis complete.")
        return json.loads(cleaned_response)
    except Exception as e:
        # The original error 'e' from the API is more informative.
        print(f"🔴 Error during Gemini API call or JSON parsing: {e}")
        return None

def scout_mode(url: str):
    """
    Launches browser, gets and CLEANS HTML, asks Gemini for selectors, and saves them.
    """
    print(f"🕵️‍♂️ Running in Scout Mode for: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            html = page.content()

            # --- NEW: Clean the HTML before sending to Gemini ---
            print("🧹 Cleaning HTML to reduce token count...")
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(['script', 'style', 'svg']): # Remove script, style, and svg tags
                tag.decompose()
            cleaned_html = str(soup.body) # Only send the body content
            
            # Pass the smaller, cleaned HTML to the LLM
            selectors = get_selectors_from_gemini(cleaned_html)
            
            if selectors:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(selectors, f, indent=2)
                print(f"✅ Configuration saved successfully to {CONFIG_FILE}")
            else:
                print("🔴 Scout mode failed. Could not generate selectors.")
        
        except Exception as e:
            print(f"🔴 An error occurred in Scout Mode: {e}")
        finally:
            browser.close()

# ... The 'scrape_mode' and 'if __name__ == "__main__":' sections remain unchanged ...
def scrape_mode(url: str):
    """
    Loads selectors from config file and performs a fast, multi-page scrape.
    """
    print(f"⚡ Running in Fast Scrape Mode for: {url}")
    if not os.path.exists(CONFIG_FILE):
        print(f"🔴 Config file '{CONFIG_FILE}' not found. Please run Scout Mode first.")
        return

    with open(CONFIG_FILE, 'r') as f:
        selectors = json.load(f)

    print(f"✅ Loaded selectors: {selectors}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page_count = 1
            
            while True:
                print(f"\n--- Scraping Page {page_count} ---")
                page.wait_for_selector(selectors['job_item'], timeout=30000)
                job_cards = page.locator(selectors['job_item']).all()
                
                if not job_cards:
                    print("No job cards found on this page. Exiting.")
                    break

                for card in job_cards:
                    title = card.locator(selectors['title']).inner_text().strip()
                    location = card.locator(selectors['location']).first.inner_text().strip()
                    print(f"  - Title: {title}\n    Location: {location}")
                
                # Pagination logic
                next_button = page.locator(selectors['pagination_next'])
                if not next_button.is_visible() or next_button.is_disabled():
                    print("\n✅ Reached the last page or 'Next' button is not available.")
                    break
                
                next_button.click()
                print("\nNavigating to next page...")
                # Wait for new content to settle
                page.wait_for_load_state("networkidle", timeout=60000)
                page_count += 1

        except Exception as e:
            print(f"🔴 An error occurred during scraping: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An intelligent scraper using Gemini and Playwright.")
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Operating mode")

    # Scout mode parser
    parser_scout = subparsers.add_parser("scout", help="Analyze a website with Gemini and create a config file.")
    parser_scout.add_argument("--url", required=True, help="The URL of the job listings page to scout.")

    # Scrape mode parser
    parser_scrape = subparsers.add_parser("scrape", help="Scrape a website using an existing config file.")
    parser_scrape.add_argument("--url", required=True, help="The URL of the job listings page to scrape.")

    args = parser.parse_args()

    if args.mode == "scout":
        scout_mode(args.url)
    elif args.mode == "scrape":
        scrape_mode(args.url)