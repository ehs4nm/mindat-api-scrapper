import requests
import json
import time

# Your Mindat.org API token
# Replace 'YOUR_TOKEN' with your actual token
API_TOKEN = '5bece3c1ed62c85ddb63a8a43362b24f'

# Base URL for the API endpoint
BASE_URL = 'https://api.mindat.org/v1/geomaterials/'

# Headers for authentication and content type
headers = {
    'Authorization': f'Token {API_TOKEN}',
    'Accept': 'application/json'
}

def fetch_all_geomaterials(base_url, headers):
    """
    Fetches all pages of data from the Mindat geomaterials API.
    Handles pagination by following the 'next' URL in the response.
    """
    all_data = []
    current_url = base_url

    print("Starting data download from Mindat.org API...")
    
    while current_url:
        try:
            print(f"Fetching data from: {current_url}")
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()
            
            # Append the results from the current page to our list
            all_data.extend(data.get('results', []))
            
            # Get the URL for the next page
            current_url = data.get('next')
            
            # Be a good citizen and add a small delay to avoid overwhelming the API
            if current_url:
                time.sleep(1) # Delay of 1 second between requests
        
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break
            
    print(f"Download complete. Total items fetched: {len(all_data)}")
    return all_data

def save_data_to_json(data, filename='geomaterials_data.json'):
    """
    Saves a list of data dictionaries to a JSON file.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Data successfully saved to {filename}")
    except IOError as e:
        print(f"Error saving file: {e}")

if __name__ == '__main__':
    # Fetch all data from the API
    geomaterials_data = fetch_all_geomaterials(BASE_URL, headers)

    # Save the fetched data to a JSON file
    if geomaterials_data:
        save_data_to_json(geomaterials_data)