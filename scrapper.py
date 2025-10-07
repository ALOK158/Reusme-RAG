import os
import json
import argparse
import time
from urllib.parse import urljoin

import google.generativeai as genai
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# --- Configuration ---
# Load environment variables from a .env file
load_dotenv()

# Get API key and configure the Gemini model
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("🔴 GOOGLE_API_KEY not found in .env file. Please create it before running.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Define file names for configuration and output
CONFIG_FILE = 'config.json'
OUTPUT_FILE = 'scraped_jobs.json'

# --- Gemini Functions ---

def get_list_page_selectors_from_gemini(html_content: str) -> dict:
    """Analyzes the JOB LISTINGS page HTML to get navigation selectors."""
    print("🤖 Contacting Gemini to analyze listings page...")
    prompt = """
    You are an expert web scraping assistant. Analyze the provided HTML of a company's job listings page.
    Your task is to identify the CSS selectors for the following elements:

    1. The container for each individual job posting (key: "job_item").
    2. The job title within that container (key: "title").
    3. The job location within that container (key: "location").
    4. The link to the detailed job page within that container (key: "job_url"). This must be an 'a' tag.
    5. The link/button to click for the NEXT page of results (key: "pagination_next").

    You MUST return your response as a single, raw JSON object, and nothing else.
    Example:
    {
      "job_item": "div.job-card",
      "title": "h2.job-title",
      "location": "span.location",
      "job_url": "a.job-link",
      "pagination_next": "a.next-page"
    }
    """
    try:
        # Clean HTML before sending to reduce tokens and improve focus
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup(['script', 'style', 'svg', 'header', 'footer', 'nav']):
            tag.decompose()
        
        response = model.generate_content([prompt, str(soup.body)])
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        print("✅ Gemini analysis of list page complete.")
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"🔴 Error during Gemini list page analysis: {e}")
        return None


def get_job_details_from_gemini(html_chunk: str) -> dict:
    """Analyzes a filtered HTML chunk of a JOB DETAIL page to extract structured data."""
    print("    🤖 Contacting Gemini to extract job details...")
    prompt = """
    You are an expert data extraction assistant. Analyze the provided HTML of a single job posting.
    Your task is to extract the following information:

    1. A list of all job requirements or qualifications (key: "requirements").
    2. A list of all job responsibilities or duties (key: "responsibilities").
    3. The job type, if mentioned (e.g., "Full-time", "Contract") (key: "job_type").

    If a section is not found, return an empty list or null for that key.
    You MUST return your response as a single, raw JSON object, and nothing else.
    Example:
    {
      "requirements": [
        "5+ years of experience with Python.",
        "Bachelor's degree in Computer Science.",
        "Experience with cloud platforms (AWS, GCP, or Azure)."
      ],
      "responsibilities": [
        "Develop and maintain web applications.",
        "Collaborate with cross-functional teams.",
        "Write clean, scalable code."
      ],
      "job_type": "Full-time"
    }
    """
    try:
        response = model.generate_content([prompt, html_chunk])
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        print("    ✅ Gemini extraction of job details complete.")
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"    🔴 Error during Gemini detail page extraction: {e}")
        return {"requirements": [], "responsibilities": [], "job_type": "Not found"}



# REPLACE your old filter_with_beautifulsoup function with this one

def filter_with_beautifulsoup(html: str) -> str:
    """
    A more advanced filter specifically for job description pages.
    It finds multiple relevant sections (qualifications, responsibilities)
    and combines them into a single, focused HTML chunk.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Keywords to identify the start of relevant sections
    keywords = ['qualifications', 'responsibilities']
    
    relevant_chunks = []
    
    # Google Careers uses <h3> for these titles. This is a common tag.
    for header in soup.find_all(['h2', 'h3']):
        header_text = header.get_text(strip=True).lower()
        
        # Check if the header text contains any of our keywords
        if any(keyword in header_text for keyword in keywords):
            print(f"    - BeautifulSoup found relevant section: '{header.get_text(strip=True)}'")
            
            # Add the header itself to our chunk
            relevant_chunks.append(str(header))
            
            # Find the content that follows the header, usually in a <ul> list
            # We'll grab all sibling elements until we hit the next header
            for sibling in header.find_next_siblings():
                # Stop if we hit another header, which marks a new section
                if sibling.name in ['h2', 'h3']:
                    break
                # Otherwise, add the sibling to our chunk
                relevant_chunks.append(str(sibling))

    if relevant_chunks:
        # Join all the collected pieces into a single HTML string
        focused_html = "".join(relevant_chunks)
        return focused_html
    else:
        # Fallback if our keyword search fails
        print("    - BeautifulSoup couldn't find keyworded sections, falling back to body.")
        for tag in soup.body(['script', 'style', 'svg', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        return str(soup.body) if soup.body else ""

# --- Scraper Modes ---

def scout_mode(url: str):
    """Launches browser, gets HTML, asks Gemini for list page selectors, and saves them."""
    print(f"🕵️‍♂️ Running in Scout Mode for: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            print(f"Navigating to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("Waiting for page to settle...")
            time.sleep(5)  # Wait for any dynamically loaded content
            
            html = page.content()
            
            selectors = get_list_page_selectors_from_gemini(html)
            
            if selectors:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(selectors, f, indent=4)
                print(f"\n✅ Configuration saved successfully to {CONFIG_FILE}")
                print(f"Generated Selectors: {json.dumps(selectors, indent=2)}")
            else:
                print("\n🔴 Scout mode failed. Could not generate selectors.")
        
        except Exception as e:
            print(f"🔴 An error occurred in Scout Mode: {e}")
        finally:
            browser.close()

def scrape_mode(url: str):
    """Loads config, scrapes list pages, and visits each job link to extract details using the hybrid approach."""
    print(f"⚡ Running in Scrape Mode for: {url}")
    if not os.path.exists(CONFIG_FILE):
        print(f"🔴 Config file '{CONFIG_FILE}' not found. Please run Scout Mode first using: python your_script_name.py scout --url {url}")
        return

    with open(CONFIG_FILE, 'r') as f:
        selectors = json.load(f)

    print(f"✅ Loaded selectors: {json.dumps(selectors, indent=2)}")
    
    all_jobs_data = []

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
                    print("No more job cards found on this page.")
                    break

                for i, card in enumerate(job_cards):
                    title = card.locator(selectors['title']).inner_text().strip()
                    location = card.locator(selectors['location']).first.inner_text().strip()
                    print(f"\n  - ({i+1}/{len(job_cards)}) Processing Job: {title}")

                    job_data = {"title": title, "location": location}

                    try:
                        # Get the URL for the detail page
                        job_link_element = card.locator(selectors['job_url'])
                        relative_url = job_link_element.get_attribute('href')
                        absolute_url = urljoin(url, relative_url)
                        job_data['source_url'] = absolute_url

                        # Open detail page in a new tab
                        detail_page = browser.new_page()
                        detail_page.goto(absolute_url, wait_until="domcontentloaded", timeout=60000)
                         # ADD THIS LINE to wait for the content to appear
                        print("    - Waiting for job details to load...")
                        detail_page.wait_for_selector("h3:has-text('Minimum qualifications')")
                        
                        detail_html = detail_page.content()
                        
                        # Use BeautifulSoup to filter down to the most relevant HTML chunk
                        filtered_html_chunk = filter_with_beautifulsoup(detail_html)
                        
                        # Use Gemini to extract structured details from the filtered chunk
                        extracted_details = get_job_details_from_gemini(filtered_html_chunk)
                        job_data.update(extracted_details)

                        detail_page.close()
                    except Exception as e:
                        print(f"    🔴 Could not scrape details for '{title}': {e}")
                        job_data['error'] = str(e)
                    
                    all_jobs_data.append(job_data)
                    # Optional: Short delay to be polite to the server
                    time.sleep(1)

                # --- Pagination Logic ---
                next_button = page.locator(selectors['pagination_next'])
                if not next_button.is_visible() or next_button.is_disabled():
                    print("\n✅ Reached the last page or 'Next' button is not available.")
                    break
                
                print("\nNavigating to next page...")
                next_button.click()
                page.wait_for_load_state("networkidle", timeout=60000) # Wait for page to settle
                page_count += 1
        
        except Exception as e:
            print(f"🔴 An error occurred during scraping: {e}")
        finally:
            if all_jobs_data:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(all_jobs_data, f, indent=4, ensure_ascii=False)
                print(f"\n✅ Scraping complete. Saved {len(all_jobs_data)} jobs to {OUTPUT_FILE}.")
            else:
                print("\nNo jobs were scraped.")
            browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An intelligent job scraper using a hybrid approach with Gemini, Playwright, and BeautifulSoup.")
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Operating mode")

    # Scout mode parser
    parser_scout = subparsers.add_parser("scout", help="Analyze a job listings page with Gemini to create a config file.")
    parser_scout.add_argument("--url", required=True, help="The URL of the main job listings page to scout.")

    # Scrape mode parser
    parser_scrape = subparsers.add_parser("scrape", help="Scrape a website using an existing config file.")
    parser_scrape.add_argument("--url", required=True, help="The starting URL of the job listings page to scrape.")

    args = parser.parse_args()

    if args.mode == "scout":
        scout_mode(args.url)
    elif args.mode == "scrape":
        scrape_mode(args.url)