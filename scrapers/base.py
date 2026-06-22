from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    id: str
    source: str
    title: str
    company: str
    url: str
    salary: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    def format_message(self) -> str:
        lines = [
            f"🔔 <b>{self.title}</b>",
            f"🏢 {self.company}",
        ]
        if self.salary:
            lines.append(f"💰 {self.salary}")
        if self.location:
            lines.append(f"📍 {self.location}")
        if self.experience:
            lines.append(f"⏳ {self.experience}")
        if self.tags:
            lines.append(f"🏷 {' '.join('#' + t.replace(' ', '_') for t in self.tags[:5])}")
        lines.append(f"🌐 {self.source}")
        lines.append(f"🔗 <a href='{self.url}'>Открыть вакансию</a>")
        return "\n".join(lines)


class BaseScraper:
    SOURCE_NAME = "unknown"

    def fetch(self, keywords: list[str]) -> list[Job]:
        raise NotImplementedError
