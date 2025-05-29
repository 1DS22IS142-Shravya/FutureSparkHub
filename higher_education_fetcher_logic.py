# /my_career_portal/higher_education_fetcher_logic.py
import requests
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLE_API_KEY_PLACES = os.getenv("GOOGLE_API_KEY")
UNSPLASH_ACCESS_KEY_EDU = os.getenv("UNSPLASH_ACCESS_KEY")

def search_google_places_api_edu(query, api_key):
    if not api_key:
        print("ERROR (Edu Fetcher): Google API Key not provided for Places search.")
        return []
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": api_key, "language": "en"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Places API for Education: {e}")
        return []

def get_google_photo_url_api_edu(photo_reference: str, api_key: str, maxwidth: int = 400) -> str:
    if not api_key or not photo_reference: return ""
    return (
        f"https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={maxwidth}&photoreference={photo_reference}&key={api_key}"
    )

def get_unsplash_image_api_edu(query: str, access_key: str) -> str:
    if not access_key:
        print("WARNING (Edu Fetcher): Unsplash Access Key not provided.")
        return "https://source.unsplash.com/600x400/?university,education,library" 
    
    url = "https://api.unsplash.com/photos/random"
    unsplash_query = f"{query} university building campus architecture" # More specific query
    params = {"query": unsplash_query, "orientation": "landscape", "client_id": access_key}
    try:
        res = requests.get(url, params=params, timeout=7)
        if res.status_code == 200:
            return res.json().get("urls", {}).get("regular", "https://source.unsplash.com/600x400/?education,study")
    except requests.exceptions.RequestException as e:
        print(f"Error calling Unsplash API for Education: {e}")
    return "https://source.unsplash.com/600x400/?campus,library"

def get_wikipedia_summary_api_edu(place_name: str) -> str:
    # Remove common suffixes that might hinder search
    place_name_cleaned = place_name.replace("University of", "").replace("College", "").strip()
    search_url = "https://en.wikipedia.org/w/api.php"
    search_params = {
        "action": "query", "list": "search", "srsearch": place_name_cleaned,
        "format": "json", "utf8": "", "limit": 1
    }
    try:
        search_response = requests.get(search_url, params=search_params, timeout=7)
        search_response.raise_for_status()
        search_results = search_response.json().get("query", {}).get("search", [])
        
        if not search_results:
            return "No specific Wikipedia summary found for this institution."
        
        page_title = search_results[0]["title"]
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title.replace(' ', '_')}"
        
        summary_response = requests.get(summary_url, headers={'User-Agent': 'CareerPortalEduFetcher/1.0'}, timeout=7)
        summary_response.raise_for_status()
        summary_data = summary_response.json()
        extract = summary_data.get("extract", "No detailed description available on Wikipedia.")
        return (extract[:350] + '...') if len(extract) > 353 else extract
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wikipedia data for '{place_name_cleaned}': {e}")
        return "Could not retrieve Wikipedia summary."

def search_colleges_globally_api(country: str, course_type: str, degree_level: str = None):
    if not GOOGLE_API_KEY_PLACES:
        print("ERROR (Edu Fetcher): GOOGLE_API_KEY is not set. Cannot perform college search.")
        return [{"name": "API Key Missing", "country": country, "error": "Google API Key not configured on server."}]

    query_parts = ["top"]
    if degree_level and degree_level != "Any": query_parts.append(degree_level)
    query_parts.append(course_type)
    query_parts.append("universities" if "university" not in course_type.lower() else "colleges") # Try to be smart
    if country: query_parts.extend(["in", country])
    
    query = " ".join(query_parts)
    print(f"Edu Fetcher: Searching Google Places with query: '{query}'")
    
    google_places_results = search_google_places_api_edu(query, GOOGLE_API_KEY_PLACES)
    
    colleges = []
    if not google_places_results:
        print("Edu Fetcher: No results from Google Places API.")
        return []

    for place in google_places_results: # Process more results, frontend can limit display
        name = place.get("name", "N/A")
        address = place.get("formatted_address", "N/A")
        
        image_url = ""
        if "photos" in place and place["photos"]:
            photo_ref = place["photos"][0].get("photo_reference")
            if photo_ref: image_url = get_google_photo_url_api_edu(photo_ref, GOOGLE_API_KEY_PLACES)
        
        if not image_url: # Fallback to Unsplash
            image_url = get_unsplash_image_api_edu(f"{name} {country or ''}", UNSPLASH_ACCESS_KEY_EDU)

        description = get_wikipedia_summary_api_edu(name)
        
        college_data = {
            "name": name, "address": address, "country": country,
            "website": place.get("website"), "rating": place.get("rating"),
            "image_url": image_url, "description": description,
            "programs": [course_type] # This is a simplified representation
        }
        colleges.append(college_data)
        if len(colleges) >= 8: # Limit the number of results processed/returned
            break
            
    return colleges