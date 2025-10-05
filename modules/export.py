from __future__ import annotations
from typing import Iterable, Sequence
from pathlib import Path
import csv

from .models import SystemCandidate, CSV_COLUMNS

def ensure_export_dir() -> Path:
  export_dir = Path(__file__).parent.parent / "export"
  export_dir.mkdir(parents=True, exist_ok=True)
  return export_dir

def write_csv(candidates: list[SystemCandidate], path: Path) -> None:
  with path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for c in candidates:
      writer.writerow(c.to_csv_row())

def _row_with_formatting(row: dict, columns: Sequence[str]) -> dict:
    #to help with consistent formatting and clean up empty values
    out = {}
    for k in columns:
        v = row.get(k, "")
        if isinstance(v, float):
            v = f"{v:.2f}"  # nicer in viewers
        out[k] = v
    return out

def write_csv(
    candidates: Iterable, path: Path, *,
    columns: Sequence[str] = CSV_COLUMNS,
    sort_key = None,
    reverse: bool = False,
) -> Path:

    items = list(candidates)
    if sort_key is not None:
        items.sort(key=sort_key, reverse=reverse)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(columns))
        writer.writeheader()
        for c in items:
            writer.writerow(_row_with_formatting(c.to_csv_row(), columns))
    return path

def autosave_csv(
    candidates: Iterable,
    *,
    base_name: str = "system_candidates",
    columns: Sequence[str] = CSV_COLUMNS,
    sort_key = None,
    reverse: bool = False,
) -> Path:
    
    #save to export/<base_name>.csv (overwrites each run for reproducibility).
    
    export_dir = ensure_export_dir()
    out_path = export_dir / f"{base_name}.csv"
    return write_csv(candidates, out_path, columns=columns, sort_key=sort_key, reverse=reverse)


def test() -> None:
  a = SystemCandidate(name="Alpha Centauri", distance_ly=4.37, planet_count=3)
  a.add_note("demo entry")

  b = SystemCandidate(name="Barnard's Star", distance_ly=5.967, planet_count=1)
  b.add_note("another demo")  

  c = SystemCandidate(name="Wolf 1061", distance_ly=13.8, planet_count=3)
  c.add_note("third demo")  

  d = SystemCandidate(name="Unknown", distance_ly=12.36, planet_count=2, data_ok=False)
  d.add_note("fourth demo") 

  #sort for demo
  candidates = []

  for sys in (a, b, c, d):
    if sys.data_ok:
      candidates.append(sys)  

  out_path = autosave_csv(
    candidates,
    base_name="export_test",
    columns=CSV_COLUMNS,
    sort_key=lambda x: x.distance_ly,
    reverse=False,
  )
  print(f"Wrote {len(candidates)} candidates to {out_path}")

  

if __name__ == "__main__":
  test()