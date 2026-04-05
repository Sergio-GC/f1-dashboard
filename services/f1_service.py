import requests
from datetime import datetime, timezone, timedelta
from cachetools import TTLCache

from config import JOLPICA_BASE_URL, CACHE_TTL, API_CALL_TIMEOUT


_cache = TTLCache(maxsize=32, ttl=CACHE_TTL)

def _api_get(path, params=None):
    """Call the Jolpica API."""
    url = f"{JOLPICA_BASE_URL}{path}.json"
    response = requests.get(url, params=params, timeout=API_CALL_TIMEOUT)
    response.raise_for_status()
    
    return response.json()


def _utc_to_cet_date_format(date_str, time_str):
    """Format an UTC date + time into a more readable string in CET timezone"""
    from zoneinfo import ZoneInfo
    try:
        # Format the date + time into a readable string and convert it to CET timezone
        date = datetime.strptime(f"{date_str}T{time_str}", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        cet = date.astimezone(ZoneInfo("Europe/Paris"))

        # Return the formatted date time in a correct format
        return cet.strftime("%a %d %b %Y, %H:%M %Z")
    except Exception as e:
        print(f"Date format error: {e}\nDate_str: {date_str}\nTime_str: {time_str}")
        return f""


def _build_race_data(race):
    """Transform raw json data from the api in a clean format"""
    # Make sure we do have a rece to work on
    if not race:
        return None
    
    circuit = race["Circuit"]

    sessions = {}
    is_sprint = False

    for api_key, label in [
        ("Qualifying", "qualifying"),
        ("Sprint", "sprint"),
        ("SprintQualifying", "sprint_qualifying")
    ]:
        if api_key in race:
            session = race[api_key]
            sessions[label] = {
                "display": _utc_to_cet_date_format(session["date"], session.get("time", "00:00:00Z")),
                "utc": f"{race['date']}T{session.get('time', '00:00:00Z')}"
            }

            is_sprint = api_key in ("Sprint", "SprintQualifying")

    sessions["race"] = {
        "display": _utc_to_cet_date_format(race["date"], race.get("time", "00:00:00Z")),
        "utc": f"{race['date']}T{race.get('time', '00:00:00Z')}"
    }

    return {
        "name": race["raceName"],
        "round": race["round"],
        "date": race["date"],
        "time": race.get("time", "00:00:00Z"),
        "circuit_name": circuit["circuitName"],
        "circuit_id": circuit["circuitId"],
        "locality": circuit["Location"]["locality"],
        "country": circuit["Location"]["country"],
        "lat": circuit["Location"]["lat"],
        "long": circuit["Location"]["long"],
        "sessions": sessions,
        "is_sprint": is_sprint,
    }


def _laptime_to_seconds(time_str):
    """Convert laptime in string to seconds"""
    try:
        parts = time_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except Exception:
        return 9999



def get_current_races():
    """Fetch the next and last races from the current season.\nReturns (next_race, last_race) tuple."""
    if "current_races" in _cache:
        return _cache["current_races"]
    
    # Get the race list from the api
    data = _api_get("current", {"limit":30})
    race_list = data["MRData"]["RaceTable"]["Races"]

    # Get the current date
    now = datetime.now(timezone.utc)

    next_race = None
    last_race = None

    for race in race_list:
        race_time = race.get("time", "23:59:59Z")
        
        try:
            race_date = datetime.strptime(f"{race['date']}T{race_time}", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        if race_date > now:
            if next_race is None:
                next_race = race
                break
        else:
            last_race = race

    # Format the races
    result = (_build_race_data(next_race), _build_race_data(last_race))

    # Store the data in the cache and return
    _cache["current_races"] = result
    return result


def get_last_race_results(last_race):
    """Get the last race's results"""
    _cache_label = "last_race_results"

    if _cache_label in _cache:
        return _cache[_cache_label]
    
    if not last_race:
        return None
    
    # Extract the round number from the last race object
    round_number = last_race["round"]
    # Get the results from the api by sending the round
    data = _api_get(f"current/{round_number}/results", {"limit": 20})
    races = data["MRData"]["RaceTable"]["Races"]

    if not races:
        return None
    
    race = races[0]
    results = []

    for result in race.get("Results", [])[:30]:
        driver = result["Driver"]
        fastest_lap = result.get("FastestLap", {})
        results.append({
            "pos": result.get("position", "-"),
            "name": f"{driver['givenName']} {driver['familyName']}",
            "code": driver.get("code", "---"),
            "team": result["Constructor"]["name"],
            "grid": result.get("grid", "-"),
            "status": result.get("status", ""),
            "points": float(result.get("points", 0)),
            "fastest_lap": fastest_lap.get("rank") == "1"
        })


    res = {
        "race_name": race.get("raceName"),
        "round": round_number,
        "results": results
    }

    # Cache and return
    _cache[_cache_label] = results
    return results


def get_laptime_record(circuit_id):
    """Get the all time best lap time"""
    cache_key = f"lap_record_{circuit_id}"
    if cache_key in _cache:
        return _cache[cache_key]

    data = _api_get(
        f"circuits/{circuit_id}/fastest/1/results",
        {"limit": 100},
    )
    races = data["MRData"]["RaceTable"]["Races"]

    best = None
    best_secs = 9999

    for race in races:
        for result in race.get("Results", []):
            fast_lap = result.get("FastestLap", {})
            time_str = fast_lap.get("Time", {}).get("time", "")

            if not time_str:
                return None
            
            time_in_seconds = _laptime_to_seconds(time_str)
            if time_in_seconds < best_secs:
                best_secs = time_in_seconds
                best = {
                    "time": time_str,
                    "driver": f"{result['Driver']['givenName']} {result['Driver']['familyName']}",
                    "year": race.get("season", "")
                }


    # Cache and return
    _cache[cache_key] = best
    return best


def get_driver_standings():
    """Currente season's drivers championship standings"""
    if "driver_standings" in _cache:
        return _cache["driver_standings"]
    
    # Fetch data from the api
    data = _api_get("current/driverStandings", {"limit": 30})
    lists = data["MRData"]["StandingsTable"]["StandingsLists"]

    # If the api returned nothing, return nothing too
    if not lists:
        return []
    
    # Prepare the result variable
    result = []
    for driver in lists[0]["DriverStandings"]:
        team = driver["Constructors"][0]["name"] if driver.get("Constructors") else "N/A"
        result.append({
            "pos": driver["position"],
            "driver_id": driver["Driver"]["driverId"],
            "code": driver["Driver"].get("code", "???"),
            "name": f"{driver['Driver']['givenName']} {driver['Driver']['familyName']}",
            "team": team,
            "points": driver["points"],
            "wins": driver["wins"]
        })

    _cache["driver_standings"] = result
    return result

def get_constructor_standings():
    """Current sseason's constructor championship standings"""
    if "constructor_standings" in _cache:
        return _cache["constructor_standings"]
    
    # Fetch the raw json data from the api
    data = _api_get("current/constructorStandings", {"limit": 20})
    lists = data["MRData"]["StandingsTable"]["StandingsLists"]

    # If response empty, return nothing
    if not lists:
        return []
    
    # Prepare response
    result = []
    for standing in lists[0]["ConstructorStandings"]:
        result.append({
            "pos": standing["position"],
            "name": standing["Constructor"]["name"],
            "constructor_id": standing["Constructor"]["constructorId"],
            "points": standing["points"],
            "wins": standing["wins"]
        })

    # Cache and return
    _cache["constructor_standings"] = result
    return result