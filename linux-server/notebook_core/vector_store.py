import os
import chromadb

DB_DIR = os.path.join(os.path.dirname(__file__), "db")

# Initialize ChromaDB client in persistent mode
chroma_client = chromadb.PersistentClient(path=os.path.join(DB_DIR, "chroma"))

# Create or get the collection for our notes
notes_collection = chroma_client.get_or_create_collection(name="notebook_vault")

def index_note(note_id: str, title: str, content: str):
    """Chunks and indexes the note content into ChromaDB."""
    # In a real setup, we would chunk the content into paragraphs
    # Here we index the full document as a basic implementation
    notes_collection.upsert(
        documents=[content],
        metadatas=[{"title": title}],
        ids=[note_id]
    )

def search_notes(query: str, n_results: int = 5):
    """Searches the vector database for semantically similar notes."""
    results = notes_collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results
