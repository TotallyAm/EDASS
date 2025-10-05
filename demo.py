from modules.models import CSV_COLUMNS
from modules.systems import fetch_candidates
from modules.filters import Filter
from modules.export import autosave_csv




def main():
  centre = "NGC 1514 Sector EB-X c1-3"
  radius = 30.0 #ly

  cands = fetch_candidates(centre, radius, polite_delay=0.2)
  survivors, culled = Filter().filter_candidates(
    cands,
    require_data_ok=True, 
    min_planets=0,
    require_colonisable=True,
  ) 
  Filter().print_culled_report(culled)

  autosave_csv(survivors, base_name="search_results", columns=CSV_COLUMNS, sort_key=lambda x: x.planet_count, reverse=True)

  print(f"[EDASS] Fetched {len(cands)}  | Survivors: {len(survivors)} | Culled: {len(culled)}")
  print("[EDASS] Exported filtered candidates to export/search_results.csv")
  print("[EDASS] Done.")

if __name__ == "__main__":
  main()