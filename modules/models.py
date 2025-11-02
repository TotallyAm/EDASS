from dataclasses import dataclass, field

CSV_COLUMNS = [
  "System", "Distance (ly)", "Primary star", "Stars", "Planets", "Interesting Planets", 
  "Landables", "Rings", "Notes"
]

@dataclass
class SystemCandidate:
  #core info
  name: str = "Unknown"
  distance_ly: float = 0.0
  primary_star: str = "Unknown"

  #tallies
  planet_count: int = 0
  interesting_worlds: int = 0
  landables: int = 0
  rings: int = 0
  star_count: int = 0

  #flags
  uncolonisable: bool = False
  data_ok: bool = True

  #notes
  notes: list[str] = field(default_factory=list)

  #helpers
  def add_note(self, msg: str) -> None:
    if msg and msg not in self.notes:
      self.notes.append(msg)
    
  @property
  def note_str(self) -> str:
    return "; ".join(self.notes)
    
  def to_csv_row(self) -> dict:
    row = {
        "System": self.name,
        "Distance (ly)": f"{self.distance_ly:.2f}",
        "Primary star": self.primary_star,
        "Stars": self.star_count,
        "Planets": self.planet_count,
        "Interesting Planets": self.interesting_worlds,
        "Landables": self.landables,
        "Rings": self.rings,
        "Notes": self.note_str
    }
    return row
  



