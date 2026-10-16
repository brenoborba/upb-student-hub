from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Attachment:
    name: str
    url: str


@dataclass
class Assignment:
    course: str
    title: str
    url: Optional[str] = None
    open_at: Optional[str] = None
    due_at: Optional[str] = None
    status: Optional[str] = None
    status_label: Optional[str] = None
    description: Optional[str] = None
    description_text: Optional[str] = None
    attachments: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "course": self.course,
            "assignment": self.title,
            "open_at": self.open_at,
            "due_at": self.due_at,
            "status": self.status,
            "status_label": self.status_label,
            "description": self.description,
            "description_text": self.description_text,
            "attachments": [{"name": a.name, "url": a.url} for a in self.attachments],
            "url": self.url,
        }
