from __future__ import annotations
import time, random, asyncio, httpx
from typing import Any, Optional
from .models import SystemCandidate

EDSM = "https://www.edsm.net"
ARDENT = "https://api.ardent-insight.com"
UA   = {"User-Agent": "EDASS/0.3 (+edass-local)"}

RATE = 8.0  # default max requests per second

class ApiFatalError(RuntimeError):
    pass

class RateLimiter:
    def __init__(self, rate_per_sec: float = 10.0, min_rps: float = 0.1, jitter_frac: float = 0.4):
        if rate_per_sec <= 0:
            raise ValueError("rate_per_sec must be > 0")
        
        self.target = float(rate_per_sec)
        self.current = float(rate_per_sec)
        self.min = float(min_rps)
        self.jitter_frac = max(0.0, min(jitter_frac, 0.75))
  
        self._next_ok = 0.0
        self._lock = asyncio.Lock()
        self._cooldown_until = 0.0
        self._last_success = 0.0

    def _interval(self) -> float:
        return 1.0 / max(self.current, 0.001)

    async def wait(self) -> None:
        async with self._lock:
            now = time.perf_counter()      
            if now < self._next_ok:
                await asyncio.sleep(self._next_ok - now)
                now = time.perf_counter()
            jitter = random.uniform(0.0, self.jitter_frac * self._interval())
            next_interval = self._interval() + jitter
            #print(f"\ninterval={next_interval:.4f}")  #debug
            self._next_ok = now + next_interval 

    #incase of a 429 or other rate error
    async def on_429(self, retry_after_seconds: float | None) -> None:
        async with self._lock:
            now = time.perf_counter()
            if retry_after_seconds and retry_after_seconds > 0:
                self._next_ok = max(self._next_ok, now + retry_after_seconds)
            old = self.current
            self.current = max(self.min, self.current - 0.5)

            self._cooldown_until = now + max(retry_after_seconds or 0.0, 5.0)
            if old != self.current:
                #print(f"[Limiter] 429: {old:.2f} -> {self.current:.2f} rps") #debug

    #to recover the rate after a success
    async def on_success(self):
        async with self._lock:
            now = time.perf_counter()
            if now >= self._cooldown_until and self.current < self.target:
                old = self.current
                self.current = min(self.target, self.current + 0.25)
                self._cooldown_until = now + 5.0
                if old != self.current:
                    #print(f"[Limiter] recover: {old:.2f} -> {self.current:.2f} rps") #debug



def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://www.edsm.net",
        headers=UA,
        timeout=httpx.Timeout(3.0, connect=5.0),
        follow_redirects=True,
        http2=False,
    )
        
async def _get(client: httpx.AsyncClient, limiter, url: str, params: dict | None = None, *,
                base_override: str | None = None) -> Optional[Any]:
    await limiter.wait()
    if base_override:
        full_url = f"{base_override}{url}"
        request = lambda: client.get(full_url, params=params or {})
    else:
        request = lambda: client.get(url, params=params or {})
        
    delay = 0.5
    last_status = None
    
    for attempt in range(6):
        try:
            r = await request()
            last_status = r.status_code

            if r.status_code in (429, 502, 503, 504):
                #slow down
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    try:
                        retry_after = float(ra) if ra is not None else None
                        if retry_after >= 60:
                            raise ApiFatalError(f"\n[ERROR] The API is blocking your request, retry again in {retry_after: / 60.0 :.2f} minutes")
                        else: print(f"\n[WARNING] Too many requests, retrying after {retry_after} seconds.")
                    except ValueError:
                        retry_after= None
                    await limiter.on_429(retry_after)
                else: 
                    await limiter.on_429(None)

                    
                # warn, backoff, then retry
                print(f"\n[WARNING] API request error, status code: {r.status_code}")
                
                if attempt == 5:
                    raise ApiFatalError(f"HTTP transport failed after retries (last={last_status})")

                await asyncio.sleep(delay + random.uniform(0.0, 0.2))
                delay *= 1.8
                continue

            # success path
            await limiter.on_success()
            return r.json()

        except (httpx.TimeoutException, httpx.TransportError) as e:
            if attempt == 5:
                raise ApiFatalError(f"HTTP transport failed after retries (last={last_status})")
            await asyncio.sleep(delay + random.uniform(0.0, 0.2))
            delay *= 1.8

                                
            

async def system_info(client, limiter, system_name: str) -> dict | None:
    # EDSM: /api-v1/system?systemName=...&showInformation=1
    data = await _get(client, limiter, "/api-v1/system",
        {"systemName": system_name, 
         "showInformation": 1,
         "showPermit": 1,
         "showPrimaryStar": 1}
    )
    if isinstance(data, dict):
        return data
    return None


async def search_systems(
    client, limiter, name: str, search_radius: int = 5
) -> list[dict]:
    name = name.strip()
    if not name:
        return []
    url = f"/v2/system/name/{name}/nearby"
    data = await _get(
        client, limiter, url, {"maxDistance": search_radius}, base_override=ARDENT
    )

    if isinstance(data, list):
        current_system = {"systemName": name, "distance": 0}
        data.insert(0, current_system)
        return data
    return []

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
    stars = [s for s in bodies if s.get("type") == "Star"]
    cand.planet_count = len(planets)
    cand.star_count = len(stars)

    if cand.planet_count == 0:
        cand.add_note("No planets")

    for s in stars:
        st = s.get("subType", "")
        st_strip = st.lower().strip()
        if st_strip.startswith(("o", "b")):
            cand.add_note("Has a massive star")
        if st_strip.startswith(("c", "ms", "s")):
            cand.add_note("Has a rare star")
        if st_strip.startswith(("w", "bl", "n", "su")):
            cand.add_note(f"Has {st}")
        if "giant" in st_strip or "supergiant" in st_strip:
            cand.add_note(f"Has a giant star")

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

async def system_check(client, limiter, cand: SystemCandidate) -> None: 
    raw = await system_info(client, limiter, cand.name)
    if raw is None:
        cand.data_ok = False
        cand.add_note("Bad system info")
        return
    star = raw.get("primaryStar", raw)
    info = raw.get("information", raw)
    permit_info = raw.get("permit", raw)
    
    pop = info.get("population")
    gov = info.get("government")
    
    require_permit = permit_info.get("requirePermit")

    primary_star_type = star.get("type")
    if primary_star_type:
        cand.primary_star = primary_star_type
    else:
        cand.primary_star = "Unknown"
        cand.data_ok = False
        print("[ERROR] Missing primary star type for system:", cand.name)

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

    await system_check(client, limiter, cand)

    if exclude_uncolonisable and cand.uncolonisable:
        return cand
    
    st = await stations_for(client, limiter, name)
    _tally_stations(cand, st)

    if exclude_uncolonisable and cand.uncolonisable:
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
    rate_per_sec: float = RATE,
    confirm: bool = True,
) -> list[SystemCandidate]:
    limiter = RateLimiter(RATE)
    sem = asyncio.Semaphore(max_concurrent)

    async with make_client() as client:
        raw = await search_systems(client, limiter, centre, search_radius=radius_ly)

        if not raw:
            print("[ERROR] Systems not found, please try a different search.")
            return []
        if len(raw) > 450:
            print(f"[ERROR] Too many systems found ({len(raw)}). Please narrow your search.")
            return []
        
        approx_calls = len(raw) * 2.8
        sec_min = approx_calls / rate_per_sec

        
        print(f"[EDASS] Estimated time to fetch details for {len(raw)} systems: ~{sec_min:.1f} seconds at {rate_per_sec} rps.")
        if confirm:
            ans = await asyncio.to_thread(input, "Would you like to continue? (y/n): ")
            ans = ans.strip().lower()
            if ans not in ("y", "yes"):
                print("Aborting.")
                return []
        
        total = len(raw)
        progress = 0
        lock = asyncio.Lock()

        #start the timer
        start = time.perf_counter()

        async def run_one(s):
            nonlocal progress
            async with sem:
                result = await process_system(client, limiter, s, exclude_uncolonisable=exclude_uncolonisable)
                # update progress safely
                async with lock:
                    progress += 1
                    elapsed = time.perf_counter() - start
                    print(f"\rProgress: {progress}/{total} | Elapsed: {elapsed:.1f}s", end="", flush=True)
                return result

        results = await asyncio.gather(*(run_one(s) for s in raw))
        
        #end the timer
        end = time.perf_counter()
        total_time = end - start
        print(f"\n[EDASS] Completed {total} systems in {total_time:.1f} seconds")

        return results
    
    
def fetch_candidates(
    centre: str,
    radius_ly: float,
    *,
    exclude_uncolonisable: bool = True,
    max_concurrent: int = 5,
    rate_per_sec = RATE,
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
            rate_per_sec=RATE,
            confirm=confirm,
        )
    )

import asyncio, time


