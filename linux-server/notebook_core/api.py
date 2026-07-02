import os
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import List

from .models import Note, NoteCreate, NoteRead
from .database import get_session, create_db_and_tables
from .version_control import init_repo, commit_file, VAULT_DIR
from .vector_store import index_note, search_notes
import base64
from io import BytesIO
from PIL import Image
import pytesseract

router = APIRouter(prefix="/api/notebook", tags=["notebook"])

# Initialize storage layers
@router.on_event("startup")
def on_startup():
    create_db_and_tables()
    init_repo()

# Background task worker
def process_note_background(note: Note, content: str, image_b64: str = None, enable_ocr: bool = False):
    """
    Handles saving the markdown file, committing to git, extracting OCR, and indexing to ChromaDB
    without blocking the API response thread.
    """
    try:
        # 1. Save flat markdown file
        full_path = os.path.join(VAULT_DIR, note.file_path)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # 2. Commit via Git
        commit_file(note.file_path, f"Auto-commit: Note {note.title} updated")
        
        # 3. OCR Extraction
        extracted_text = ""
        if enable_ocr and image_b64 and image_b64.startswith("data:image/png;base64,"):
            b64_data = image_b64.split(",")[1]
            try:
                img = Image.open(BytesIO(base64.b64decode(b64_data)))
                # Extract text
                extracted_text = pytesseract.image_to_string(img)
                if extracted_text.strip():
                    print(f"Extracted OCR Text: {extracted_text.strip()}")
            except Exception as e:
                print(f"OCR Error: {e}")
        
        # 4. Index into Vector Database
        # Do not index raw JSON strokes, it dilutes the text embedding!
        index_content = f"Title: {note.title}"
        if extracted_text.strip():
            index_content += f"\n\nOCR Text:\n{extracted_text}"
            
        index_note(note.id, note.title, index_content)
        
        print(f"Successfully processed note {note.id} in background.")
    except Exception as e:
        print(f"Error processing note in background: {e}")

@router.post("/notes/", response_model=NoteRead)
async def create_note(note_in: NoteCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    # 1. Create SQL Metadata
    file_name = f"{note_in.title.replace(' ', '_').lower()}.md"
    db_note = Note(title=note_in.title, tags=note_in.tags, file_path=file_name)
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    
    # 2. Enqueue background processing for file I/O, Git, and Vector DB
    background_tasks.add_task(process_note_background, db_note, note_in.content, note_in.image, note_in.enable_ocr)
    return NoteRead(**db_note.dict(), content=note_in.content)

@router.put("/notes/{note_id}", response_model=NoteRead)
async def update_note(note_id: str, note_in: NoteCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    db_note = session.get(Note, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    db_note.title = note_in.title
    db_note.tags = note_in.tags
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    
    background_tasks.add_task(process_note_background, db_note, note_in.content, note_in.image, note_in.enable_ocr)
    return NoteRead(**db_note.dict(), content=note_in.content)

@router.get("/notes/", response_model=List[NoteRead])
async def list_notes(session: Session = Depends(get_session)):
    notes = session.exec(select(Note)).all()
    results = []
    for note in notes:
        full_path = os.path.join(VAULT_DIR, note.file_path)
        content = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        results.append(NoteRead(**note.dict(), content=content))
    return results

@router.get("/search/")
async def semantic_search(query: str):
    """Perform a semantic search across all notes using ChromaDB."""
    results = search_notes(query)
    return {"query": query, "results": results}

@router.get("/download-ca")
async def download_ca():
    """Download the mkcert Root CA so users can install it on tablets."""
    # Assuming mkcert CAROOT is standard. In production, we'd dynamically read it.
    ca_path = os.path.expanduser("~/.local/share/mkcert/rootCA.pem")
    if not os.path.exists(ca_path):
        raise HTTPException(status_code=404, detail="Root CA not found")
    return FileResponse(ca_path, filename="notebook_root_ca.pem")
