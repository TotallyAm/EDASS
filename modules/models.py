from dataclasses import dataclass, field

CSV_COLUMNS = [
  "name", "distance_ly", "planet_count", "interesting_worlds", 
  "landables", "rings", "notes"
]

@dataclass
class SystemCandidate:
  #core info
  name: str = "Unknown"
  distance_ly: float = 0.0

  #tallies
  planet_count: int = 0
  interesting_worlds: int = 0
  landables: int = 0
  rings: int = 0

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
        "name": self.name,
        "distance_ly": f"{self.distance_ly:.2f}",
        "planet_count": self.planet_count,
        "interesting_worlds": self.interesting_worlds,
        "landables": self.landables,
        "rings": self.rings,
        "notes": self.note_str
    }
    return row
  



