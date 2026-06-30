import httpx
import pygeohash as pgh
from app.core.config import settings
from app.core.logging import logger

async def reverse_geocode(lat: float, lng: float) -> tuple[str, str]:
    """
    Returns (street_name, locality) using Google Maps Geocoding API.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set. Simulating reverse geocoding.")
        return "Unknown Street", "Unknown City"
        
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={settings.GOOGLE_MAPS_API_KEY}"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("results"):
                logger.warning(f"Reverse geocode failed or returned no results: {data.get('status')}")
                return "Unknown Street", "Unknown City"
                
            address_components = data["results"][0].get("address_components", [])
            street_name = "Unknown Street"
            locality = "Unknown City"
            
            for comp in address_components:
                types = comp.get("types", [])
                if "route" in types:
                    street_name = comp["long_name"]
                if "locality" in types:
                    locality = comp["long_name"]
                    
            return street_name, locality
            
    except Exception as e:
        logger.error(f"Reverse geocode exception: {str(e)}")
        return "Unknown Street", "Unknown City"

def compute_geohash(lat: float, lng: float, precision: int = 7) -> str:
    """
    Computes a geohash for a given lat/lng.
    Precision 7 = roughly 153m x 153m bounding box
    Precision 8 = roughly 38m x 19m bounding box
    """
    return pgh.encode(lat, lng, precision=precision)

def get_neighbor_geohashes(geohash: str) -> list[str]:
    """
    Returns the target geohash and its 8 immediate spatial neighbors.
    Useful for Firestore 'IN' queries across grid boundaries.
    """
    neighbors = pgh.neighbors(geohash)
    # pygeohash neighbors returns a dict like {'n': '...', 's': '...', 'ne': '...'}
    # We want a flat list of 9 hashes
    return [geohash] + list(neighbors.values())
