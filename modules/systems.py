from __future__ import annotations
import time, random, asyncio, httpx
from typing import Any, Optional
from functools import lru_cache
from .models import SystemCandidate

EDSM = "https://www.edsm.net"
ARDENT = "https://api.ardent-insight.com"
#https://api.ardent-insight.com/v2/system/name/{systemName}/nearby
UA   = {"User-Agent": "EDASS/0.2 (+edass-local)"}


class RateLimiter:
    def __init__(self, rate_per_sec: float = 6.0, jitter_frac: float = 0.2):
        self.min_interval = 1.0 / max(rate_per_sec, 1.0)
        self.jitter_frac = max(0.0, min(jitter_frac, 0.75))
        self._next_ok = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.perf_counter()
            if now < self._next_ok:
                wait_time = self._next_ok - now
                await asyncio.sleep(wait_time)
            jitter = random.uniform(0.0, self.jitter_frac * self.min_interval)
            next_interval = self.min_interval + jitter
            self._next_ok = asyncio.get_running_loop().time() + next_interval

def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://www.edsm.net",
        headers=UA,
        timeout=httpx.Timeout(15.0, connect=6.0),
        follow_redirects=True,
        http2=False,
    )
        
async def _get(client: httpx.AsyncClient, limiter, url: str, params: dict | None = None, *
               , base_override: str | None = None) -> Optional[Any]:
    await limiter.wait()
    if base_override:
        full_url = f"{base_override}{url}"
        request = lambda: client.get(full_url, params=params or {})
    else:
        request = lambda: client.get(url, params=params or {})
        
    delay = 0.5
    
    for attempt in range(4):
        try:
            r = await request()
            print(f"[GET] {base_override or 'EDSM'} {url} params={params}")
            if r.status_code in (429, 502, 503, 504):
                 raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
            return r.json()
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError):
            if attempt == 3:
                return None
            await asyncio.sleep(delay + random.uniform(0.0, 0.2))
            delay *= 1.8
                                
            

async def system_info(client, limiter, system_name: str) -> dict | None:
    # EDSM: /api-v1/system?systemName=...&showInformation=1
    data = await _get(client, limiter, "/api-v1/system",
        {"systemName": system_name, 
         "showInformation": 1,
         "showPermit": 1}
    )
    if isinstance(data, dict):
        return data
    return None


async def search_systems(client, limiter, name: str, search_radius: int = 5) -> list[dict]:
    name = name.strip()
    if not name:
        return []
    url = f"/v2/system/name/{name}/nearby"
    data = await _get(client, limiter, url, {"maxDistance": search_radius}, base_override=ARDENT)
    return data if isinstance(data, list) else []

async def stations_for(client, limiter, system_name: str) -> list[dict] | None:
    data = await _get(client, limiter, "/api-system-v1/stations", {"systemName": system_name})
    # EDSM sometimes returns a bare list, sometimes { "stations": [...] }
    if isinstance(data, dict):   return data.get("stations") or []
    if isinstance(data, list):   return data
    if data == []:               return []
    return None

async def bodies_for(client, limiter, system_name: str) -> dict | None:
    data = await _get(client, limiter, "/api-system-v1/bodies", {"systemName": system_name})
    return data if isinstance(data, dict) else None

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

def _tally_stations(cand: SystemCandidate, stations_payload: list[dict] | None) -> None:
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

async def population_check(client, limiter, cand: SystemCandidate) -> None: 
    raw = await system_info(client, limiter, cand.name)
    if raw is None:
        cand.data_ok = False
        cand.add_note("Bad system info")
        return
    info = raw.get("information", raw)
    permit_info = raw.get("permit", raw)
    pop = info.get("population")
    gov = info.get("government")
    require_permit = permit_info.get("requirePermit")
      

    if require_permit:
        cand.add_note("Permit locked")
        cand.uncolonisable = True
        
    try:
        pop_val = int(pop) if pop is not None else 0
    except (TypeError, ValueError):
        pop_val = 0
        cand.data_ok = False
        cand.add_note("Bad population data")
        
    if pop_val > 0 or (isinstance(gov, str) and gov.strip()):
        cand.uncolonisable = True
        cand.add_note(f"Population: {pop_val}" if pop_val > 0 else f"Government: {gov}")


async def process_system(client, limiter, s: dict, *, exclude_uncolonisable: bool) -> SystemCandidate:

    name = (s.get("systemName") or s.get("name") or "Unknown")
    dist = float(s.get("distance") or 0.0)
    cand = SystemCandidate(name=name, distance_ly=dist)

    await population_check(client, limiter, cand)

    if exclude_uncolonisable and cand.uncolonisable:
        print(f"[EDASS] Skipping uncolonisable system: {cand.name}")
        return cand
    
    st = await stations_for(client, limiter, name)
    _tally_stations(cand, st)

    if exclude_uncolonisable and cand.uncolonisable:
        print(f"[EDASS] Skipping uncolonisable system: {cand.name}")
        return cand
    
    bd = await bodies_for(client, limiter, name)
    _tally_bodies(cand, bd)
    
    return cand


async def fetch_candidates_async(
    centre: str,
    radius_ly: float,
    *,
    exclude_uncolonisable: bool = True,
    max_concurrent: int = 5,
    rate_per_sec: float = 6.0,
    confirm: bool = True,
) -> list[SystemCandidate]:
    limiter = RateLimiter(rate_per_sec)
    sem = asyncio.Semaphore(max_concurrent)

    async with make_client() as client:
        raw = await search_systems(client, limiter, centre, search_radius=radius_ly)

        if not raw:
            print("[EDASS] Systems not found, please try a different search.")
            return []
        if len(raw) > 300:
            print(f"[EDASS] Too many systems found ({len(raw)}). Please narrow your search.")
            return []
        
        approx_calls = len(raw) * 3
        sec_min = approx_calls / rate_per_sec
        print(f"[EDASS] Estimated time to fetch details for {len(raw)} systems: ~{sec_min:.1f} seconds")
        if confirm:
            ans = input("Would you like to continue? (y/n): ").strip().lower()
            if ans not in ("y", "yes"):
                print("Aborting.")
                return []
        async def run_one(s):
            async with sem:
                return await process_system(client, limiter, s, exclude_uncolonisable=exclude_uncolonisable)
        return await asyncio.gather(*(run_one(s) for s in raw))
    
    
def fetch_candidates(
    centre: str,
    radius_ly: float,
    *,
    exclude_uncolonisable: bool = True,
    max_concurrent: int = 5,
    rate_per_sec: float = 6.0,
    confirm: bool = True,
) -> list[SystemCandidate]:
    #Sync wrapper so the rest of the project can use this without await.
    import asyncio
    return asyncio.run(
        fetch_candidates_async(
            centre,
            radius_ly,
            exclude_uncolonisable=exclude_uncolonisable,
            max_concurrent=max_concurrent,
            rate_per_sec=rate_per_sec,
            confirm=confirm,
        )
    )