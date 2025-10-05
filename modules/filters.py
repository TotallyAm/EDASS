from __future__ import annotations
from .models import SystemCandidate
from typing import NamedTuple, Iterable

class Culled(NamedTuple):
    candidate: SystemCandidate
    reason: str

def passes_min_planets(c: SystemCandidate, min_planets: int) -> bool:
    return c.planet_count >= min_planets

def is_populated(c: SystemCandidate, *, exclude_uncolonisable: bool = True) -> bool:
    if exclude_uncolonisable and c.uncolonisable:
        return True
    return False

#removed for now, inbetween apis
'''def is_permit_locked(c: SystemCandidate, *, exclude_permit_locked: bool = True) -> bool:
    if exclude_permit_locked and c.is_permit_locked:
        return True
    return False'''

class Filter:
    def filter_candidates(
            self,
            candidates: Iterable[SystemCandidate],
            *,
            require_data_ok: bool = True,
            min_planets: int = 1,
            require_colonisable: bool = False,
    ):
        survivors: list[SystemCandidate] = []
        culled: list[Culled] = []

        for c in candidates:
            if require_data_ok and not c.data_ok:
                culled.append(Culled(c, "Data not OK"))
                continue
            if is_populated(c, exclude_uncolonisable=require_colonisable):
                culled.append(Culled(c, "Populated"))
                continue
            if not passes_min_planets(c, min_planets):
                culled.append(Culled(c, f"Fewer than {min_planets} planets"))
                continue
            '''if is_permit_locked(c, exclude_permit_locked=exclude_permit_locked):
                culled.append(Culled(c, "Permit locked"))
                continue '''

            survivors.append(c)
        return survivors, culled

    def print_culled_report(self, culled: Iterable[Culled]) -> None:
        tally: dict[str, int] = {}
        for entry in culled:
            reason = entry.reason
            tally[reason] = tally.get(reason, 0) + 1
        if not tally:
            print("[EDASS] No candidates were culled.")
            return
        print("[EDASS] Culled candidates:")
        for reason, count in tally.items():
            print(f" - {count} : {reason}")