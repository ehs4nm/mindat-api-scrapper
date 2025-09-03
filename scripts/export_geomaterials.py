#!/usr/bin/env python3
"""
Enhanced Mindat Geomaterials Data Fetcher
Fetches and processes geomaterials data from the Mindat API with improved UX
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Configuration
API_TOKEN = ''
BASE_URL = 'https://api.mindat.org/v1/geomaterials/'
HEADERS = {
    'Authorization': f'Token {API_TOKEN}',
    'Accept': 'application/json'
}

# File paths
LAST_URL_FILE = 'last_page_url.txt'
DATA_FILE = 'geomaterials_data.json'
LOG_FILE = 'fetch_log.txt'

# Fields to extract
DESIRED_FIELDS = {
    'id', 'longid', 'name', 'ima_formula', 
    'entrytype_text', 'description_short', 
    'elements', 'sigelements', 'occurrence'
}

class ProgressTracker:
    """Track and display progress information"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.total_items = 0
        self.current_page = 0
        
    def update(self, items_fetched: int, page_num: int):
        self.total_items = items_fetched
        self.current_page = page_num
        
    def get_stats(self) -> str:
        elapsed = datetime.now() - self.start_time
        rate = self.total_items / max(elapsed.total_seconds(), 1)
        return f"Items: {self.total_items} | Page: {self.current_page} | Rate: {rate:.1f}/sec | Time: {elapsed}"

def log_message(message: str, print_msg: bool = True):
    """Log message to file and optionally print to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    if print_msg:
        print(log_entry)
        
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except IOError:
        pass  # Continue even if logging fails

def extract_desired_fields(item: Dict) -> Dict:
    """Extract only the desired fields from a geomaterial item"""
    extracted = {}
    
    for field in DESIRED_FIELDS:
        if field in item and item[field] is not None:
            value = item[field]
            # Skip empty strings and zero values
            if value not in ["", 0, "0", []]:
                extracted[field] = value
                
    return extracted

def load_existing_data() -> List[Dict]:
    """Load existing data from file if it exists"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log_message(f"Loaded {len(data)} existing records")
                return data
        except (json.JSONDecodeError, IOError) as e:
            log_message(f"Error loading existing data: {e}")
            return []
    return []

def load_last_url() -> Optional[str]:
    """Load the last processed URL for resuming"""
    if os.path.exists(LAST_URL_FILE):
        try:
            with open(LAST_URL_FILE, 'r') as f:
                url = f.read().strip()
                if url:
                    log_message(f"Resuming from: {url}")
                    return url
        except IOError:
            pass
    return None

def save_progress(data: List[Dict], next_url: Optional[str]):
    """Save current progress to files"""
    try:
        # Save data
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Save last URL
        with open(LAST_URL_FILE, 'w') as f:
            f.write(next_url if next_url else '')
            
    except IOError as e:
        log_message(f"Error saving progress: {e}")

def fetch_page(url: str, retries: int = 3) -> Optional[Dict]:
    """Fetch a single page with retry logic"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            wait_time = 2 ** attempt  # Exponential backoff
            log_message(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                log_message(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                log_message(f"Failed to fetch {url} after {retries} attempts")
                return None
    return None

def display_sample_data(data: List[Dict], num_samples: int = 3):
    """Display sample data to show what's being collected"""
    if not data:
        return
        
    print(f"\n📋 Sample of collected data (showing {min(num_samples, len(data))} items):")
    print("=" * 80)
    
    for i, item in enumerate(data[:num_samples]):
        print(f"\nSample {i + 1}:")
        for key, value in item.items():
            if isinstance(value, list):
                value_str = f"[{', '.join(map(str, value[:3]))}{'...' if len(value) > 3 else ''}]"
            else:
                value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            print(f"  {key}: {value_str}")
    print("=" * 80)

def main():
    """Main application function"""
    print("🔬 Enhanced Mindat Geomaterials Data Fetcher")
    print("=" * 50)
    
    # Initialize progress tracker
    progress = ProgressTracker()
    
    # Load existing data
    all_data = load_existing_data()
    
    # Determine starting URL
    current_url = load_last_url() or BASE_URL
    
    if current_url == BASE_URL:
        log_message("Starting fresh download...")
    else:
        log_message(f"Resuming download from page...")
    
    page_count = 0
    
    try:
        while current_url:
            page_count += 1
            log_message(f"📄 Fetching page {page_count}...")
            
            # Fetch page data
            page_data = fetch_page(current_url)
            if not page_data:
                log_message("❌ Failed to fetch page, stopping...")
                break
            
            # Process results
            results = page_data.get('results', [])
            if not results:
                log_message("No results found on this page")
                break
                
            # Extract desired fields from each item
            processed_items = [extract_desired_fields(item) for item in results]
            # Filter out empty items
            processed_items = [item for item in processed_items if item]
            
            all_data.extend(processed_items)
            
            # Update progress
            progress.update(len(all_data), page_count)
            
            # Get next URL
            current_url = page_data.get('next')
            
            # Save progress
            save_progress(all_data, current_url)
            
            # Display progress
            stats = progress.get_stats()
            print(f"✅ {stats}")
            
            # Rate limiting
            if current_url:
                time.sleep(1)  # Be nice to the API
                
        # Final summary
        print(f"\n🎉 Download Complete!")
        print(f"📊 Total items collected: {len(all_data)}")
        print(f"📁 Data saved to: {DATA_FILE}")
        print(f"📜 Log saved to: {LOG_FILE}")
        
        # Show sample data
        if all_data:
            display_sample_data(all_data)
            
        # Clean up tracking files
        if os.path.exists(LAST_URL_FILE):
            os.remove(LAST_URL_FILE)
            log_message("Removed progress tracking file (download complete)")
        
    except KeyboardInterrupt:
        print(f"\n⏸️  Download interrupted by user")
        print(f"📊 Collected {len(all_data)} items before interruption")
        print(f"▶️  Run again to resume from where you left off")
        log_message(f"Download interrupted. Collected {len(all_data)} items.")
        
    except Exception as e:
        log_message(f"Unexpected error: {e}")
        print(f"❌ An error occurred: {e}")
        
    finally:
        # Always save what we have
        if all_data:
            save_progress(all_data, current_url)

if __name__ == '__main__':
    main()