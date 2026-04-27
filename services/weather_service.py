import requests
from cachetools import TTLCache


_cache = TTLCache(maxsize=1, ttl=1800) # 30 minutes
_endpoint = "https://api.open-meteo.com/v1/forecast"


def _weather_code_to_text(code):
    """Convert WMO weather code to a readable string."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return codes.get(code, "Unknown")


def get_race_weather(lat, long, race_date):
    """Get weather forecast for a given place at a given date"""
    cache_key = f"weather_{lat}_{long}_{race_date}"

    if cache_key in _cache:
        return _cache[cache_key]
    

    try:
        response = requests.get(
            _endpoint, 
            params={
                "latitude": lat,
                "longitude": long,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                "start_date": race_date,
                "end_date": race_date,
                "timezone": "UTC",
            },
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

    except Exception as e :
        print(f"Weather API request error: {e}")
        return None

    daily = data.get("daily", {})
    if not daily or not daily.get("time"):
        return None
    
    result = {
        "temp_max": daily["temperature_2m_max"][0],
        "temp_min": daily["temperature_2m_min"][0],
        "rain_chance": daily["precipitation_probability_max"][0],
        "condition": _weather_code_to_text(daily["weathercode"][0]),
    }

    _cache[cache_key] = result
    return result
