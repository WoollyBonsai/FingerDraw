import uuid
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class NoteBase(SQLModel):
    title: str = Field(index=True)
    tags: Optional[str] = Field(default=None, description="Comma separated tags")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Note(NoteBase, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    file_path: str = Field(description="Relative path to the flat markdown file")
    
class NoteCreate(NoteBase):
    content: str
    image: Optional[str] = Field(default=None, description="Base64 encoded PNG of the canvas")
    
class NoteRead(NoteBase):
    id: str
    content: str
