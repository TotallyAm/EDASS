import time 
from modules.models import CSV_COLUMNS
from modules.systems import fetch_candidates
from modules.filters import Filter
from modules.export import autosave_csv
from modules.input import user_input


def main():
  centre, radius_ly, min_planets, exclude_uncolonisable = user_input()
  cands = fetch_candidates(    
    centre=centre,
    radius_ly=radius_ly,
    exclude_uncolonisable=exclude_uncolonisable,
    max_concurrent=4,
    confirm=True,
    )
  

  survivors, culled = Filter().filter_candidates(
    cands,
    require_data_ok=True, 
    min_planets=min_planets,
    require_colonisable=exclude_uncolonisable,
  ) 
  

  autosave_csv(survivors, base_name="search_results", columns=CSV_COLUMNS, sort_key=lambda x: x.planet_count, reverse=True)

  if len(cands) > 0:
    Filter().print_culled_report(culled)
    print(f"[EDASS] Fetched {len(cands)}  | Survivors: {len(survivors)} | Culled: {len(culled)}")
    print("[EDASS] Exported filtered candidates to export/search_results.csv")
    print("[EDASS] Done.")
  else: print("[EDASS] No candidates processed.")

main()