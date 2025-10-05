from __future__ import annotations
import time, random
import requests
from typing import Any
from .models import SystemCandidate

BASE = "https://www.edsm.net"
ARDENT_API = "https://api.ardent-insight.com/v2/system/name/"
#https://api.ardent-insight.com/v2/system/name/{systemName}/nearby
UA   = {"User-Agent": "EDASS/0.1 (+edass-local)"}



def _get_edsm(path: str, params: dict | None = None) -> Any | None:
    #Get a JSON endpoint; return parsed JSON or None on error.
    if not path.startswith("/"):
        path = "/" + path
    url = f"{BASE}{path}"
    print(f"[EDASS] Requesting: {url} with {params}")
    try:
        r = requests.get(url, params=params or {}, headers=UA, timeout=20)
        if r.status_code in (429, 503):
            print(f"[EDSM] Rate limited or service unavailable: {r.status_code}")
            print("[EDSM] Waiting 30 seconds before retrying...")
            time.sleep(30)  # wait a bit before retrying
            r = requests.get(url, params=params or {}, headers=UA, timeout=20)
        r.raise_for_status()
        return r.json()
    except ValueError as e:  # JSON decode error
        print(f"[EDSM] JSON decode {url} params={params} -> {e}")
        return None
    except requests.RequestException as e:
        print(f"[EDSM] GET {url} params={params} -> {e}")
        return None
    except Exception as e:
        print(f"[EDSM] Unexpected error {url} params={params} -> {e}")
        return None
    
def _get_ardent(path: str, end: str, params: dict | None = None) -> Any | None:
    # Get a JSON endpoint; return parsed JSON or None on error.
    url = f"{ARDENT_API}{path}{end}"
    print(f"[EDASS] Requesting: {url} with {params}")
    try:
        r = requests.get(url, params=params or {}, headers=UA, timeout=20)
        r.raise_for_status()
        return r.json()
    except ValueError as e:  # JSON decode error
        print(f"[Ardent] JSON decode {url} params={params} -> {e}")
        return None
    except requests.RequestException as e:
        print(f"[Ardent] GET {url} params={params} -> {e}")
        return None
    except Exception as e:
        print(f"[Ardent] Unexpected error {url} params={params} -> {e}")
        return None

def system_info(system_name: str) -> dict | None:
    # EDSM: /api-v1/system?systemName=...&showInformation=1
    data = _get_edsm(
        "/api-v1/system",
        {"systemName": system_name, 
         "showInformation": 1,
         "showPermit": 1}
    )
    if isinstance(data, dict):
        return data
    return None


def search_systems(name: str, search_radius: int = 5) -> list[dict]:
    name = name.strip()
    if not name:
        return []
    end = "/nearby"
    params = {"maxDistance": search_radius}
    data = _get_ardent(name, end, params)
    if isinstance(data, list):
        print(f"[EDASS] Found {len(data)} systems near '{name}' within {search_radius} ly.")
        return data
    return []

def stations_for(system_name: str) -> list[dict] | None:
    data = _get_edsm("/api-system-v1/stations", {"systemName": system_name})
    # EDSM sometimes returns a bare list, sometimes { "stations": [...] }
    if isinstance(data, dict):
        return data.get("stations") or []
    if isinstance(data, list):
        return data
    if data == []:
        return []
    return None 

def bodies_for(system_name: str) -> dict | None:
    data = _get_edsm("/api-system-v1/bodies", {"systemName": system_name})
    if isinstance(data, dict):
        return data
    return None

def _tally_bodies(cand: SystemCandidate, bodies_payload: dict | None) -> None:
    if not bodies_payload or "bodies" not in bodies_payload:
        cand.data_ok = False
        cand.add_note("No body data")
        return

    bodies = bodies_payload.get("bodies") or []
    planets = [b for b in bodies if b.get("type") == "Planet"]
    cand.planet_count = len(planets)

    if cand.planet_count == 0:
        cand.add_note("No planets")

    for b in planets:
        st = b.get("subType", "")
        if st in ("Earth-like world", "Water world", "Ammonia world"):
            cand.interesting_worlds += 1
            cand.add_note(f"Has {st}")
        if b.get("isLandable"):
            cand.landables += 1
        if b.get("rings"):
            cand.rings += 1

def _tally_stations(cand: SystemCandidate, stations_payload: list[dict] | None, polite_delay: float = 1.0) -> None:
    if stations_payload is None:
        cand.data_ok = False
        cand.add_note("No station data")
        return

    for s in stations_payload:
        t = s.get("type")
        if t == "Fleet Carrier":
            cand.add_note("Has Fleet Carrier")
        elif t == "Mega ship":
            cand.uncolonisable = True
            cand.add_note("Megaship present")
        elif t:  # any other station type (outpost, starport, etc.)
            cand.uncolonisable = True
            cand.add_note("Station present")

    #if still not populated after station scan, check system info
    if not cand.uncolonisable:
        if polite_delay > 0:
            time.sleep(polite_delay)  #be nice to EDSM :3
        raw = system_info(cand.name) or {}
        info = raw.get("information", raw)
        permit_info =  raw.get("permit", raw)
        pop = info.get("population")
        gov = info.get("government")
        require_permit: bool = permit_info.get("requirePermit")
      

        if require_permit:
            cand.add_note("Permit locked")
            print(f"[EDASS] Detected permit lock on {cand.name}")
            cand.uncolonisable = True
        
        try:
            pop_val = int(pop) if pop is not None else 0
        except (TypeError, ValueError):
            pop_val = 0
            cand.data_ok = False
            cand.add_note("Bad population data")
        
        print(f"[EDASS] Detected population: {pop_val} | Detected goverment: {gov}")

        if pop_val > 0 or (isinstance(gov, str) and gov.strip()):
            cand.uncolonisable = True
            cand.add_note("Populated" if pop_val > 0 else f"Government: {gov}")

    
    


def fetch_candidates(centre: str, radius_ly: float, *, polite_delay: float = 1.0, confirm: bool = True) -> list[SystemCandidate]:
    #get all systems here, enrich with stations/bodies/notes, return candidates

    raw = search_systems(centre, search_radius=radius_ly)
    if raw == []:  # --- fallback pseudo data for testing ---
        print("[EDASS] Systems not found, please try a different search.")      
        return []
    if len(raw) > 200:
        print(f"[EDASS] Too many systems found ({len(raw)}). Please narrow your search.")
        return []
    
    time_estimate = len(raw) * polite_delay * 8  # rough estimate
    print(f"[EDASS] Estimated time to fetch details for {len(raw)} systems: ~{time_estimate:.1f} seconds")
    prompt_continue = "Would you like to continue? (y/n): "
    print(prompt_continue, end="")
    ans = input().strip().lower()
    if ans not in ("y", "yes"):
        print("Aborting.")
        return []
    out: list[SystemCandidate] = []
    for s in raw:
        jitter = polite_delay + random.uniform(-0.05, 0.05)
        name = s.get("systemName") or "Unknown"
        dist = s.get("distance") or 0.0
        cand = SystemCandidate(name=name, distance_ly=dist)
        st = stations_for(name)

        _tally_stations(cand, st, jitter)
        if jitter > 0:
            time.sleep(jitter)  #be nice to EDSM :3

        bd = bodies_for(name)
        _tally_bodies(cand, bd)
        if jitter > 0:
            time.sleep(jitter)  #be nice to EDSM :3

        print(f"[EDASS] Jitter: {jitter:.2f} seconds")
        

        out.append(cand)
    print("[EDASS] candidate info processed")
    return out


if __name__ == "__main__":
    cands = fetch_candidates("Sol", 10, polite_delay=1.0, confirm=False)
    print(len(cands), "candidates")
    for c in cands[:5]:
        print(c.name, c.distance_ly, c.planet_count, c.notes)