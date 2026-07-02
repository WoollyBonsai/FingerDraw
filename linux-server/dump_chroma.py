import sys
import os
sys.path.append('/home/woolly/Work/FingerDraw/linux-server')
import chromadb

DB_DIR = "/home/woolly/Work/FingerDraw/linux-server/notebook_core/db"
try:
    if not os.path.exists(os.path.join(DB_DIR, "chroma")):
        print("Database folder does not exist. It is empty.")
        sys.exit(0)
        
    chroma_client = chromadb.PersistentClient(path=os.path.join(DB_DIR, "chroma"))
    notes_collection = chroma_client.get_collection(name="notebook_vault")
    all_data = notes_collection.get()
    
    if len(all_data['ids']) == 0:
        print("Database is completely empty.")
        sys.exit(0)
        
    print(f"Total Notebooks in Database: {len(all_data['ids'])}")
    for i in range(len(all_data['ids'])):
        print("=" * 60)
        print(f"ID: {all_data['ids'][i]}")
        print(f"Title Metadata: {all_data['metadatas'][i]}")
        print("--- CONTENT STORED FOR SEARCH ---")
        print(all_data['documents'][i])
        print("=" * 60)
except Exception as e:
    print(f"Error accessing DB: {e}")
