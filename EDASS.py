from modules.models import CSV_COLUMNS
from modules.systems import fetch_candidates
from modules.filters import Filter
from modules.export import autosave_csv
from modules.input import user_input

centre, radius, min_planets = user_input()

def main(centre, radius, min_planets):
  cands = fetch_candidates(centre, radius, polite_delay=0.2)
  survivors, culled = Filter().filter_candidates(
    cands,
    require_data_ok=True, 
    min_planets=min_planets,
    require_colonisable=True,
  ) 
  Filter().print_culled_report(culled)

  autosave_csv(survivors, base_name="search_results", columns=CSV_COLUMNS, sort_key=lambda x: x.planet_count, reverse=True)

  print(f"[EDASS] Fetched {len(cands)}  | Survivors: {len(survivors)} | Culled: {len(culled)}")
  print("[EDASS] Exported filtered candidates to export/search_results.csv")
  print("[EDASS] Done.")

main(centre, radius, min_planets)