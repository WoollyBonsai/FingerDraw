import sys
import os
sys.path.append('/home/woolly/Work/FingerDraw/linux-server')
import chromadb

DB_DIR = "/home/woolly/Work/FingerDraw/linux-server/notebook_core/db"
try:
    chroma_client = chromadb.PersistentClient(path=os.path.join(DB_DIR, "chroma"))
    notes_collection = chroma_client.get_collection(name="notebook_vault")
    
    print("=== Query: 'hello' ===")
    res = notes_collection.query(query_texts=["hello"], n_results=5)
    print(res['distances'])
    
    print("=== Query: 'gibberish' ===")
    res = notes_collection.query(query_texts=["gibberish"], n_results=5)
    print(res['distances'])
    
    print("=== Query: 'n' ===")
    res = notes_collection.query(query_texts=["n"], n_results=5)
    print(res['distances'])

except Exception as e:
    print(f"Error accessing DB: {e}")
