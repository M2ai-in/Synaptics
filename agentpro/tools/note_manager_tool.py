from agentpro.tools.base import Tool
from sentence_transformers import SentenceTransformer
from typing import List, Any
import numpy as np
import faiss
class FAISSVectorDB:
    def __init__(self, index, note_store):
        self.index = index
        self.note_store = note_store
    def similarity_search(self, query_embedding, k=5):
        if self.index.ntotal == 0: return []
        query_vector = np.array(query_embedding).astype("float32").reshape(1, -1)
        scores, indices = self.index.search(query_vector, k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.note_store):
                results.append({"text": self.note_store[idx]["text"], "score": float(scores[0][i])})
        return results
class NoteManager(Tool):
    name: str = "note_manager"
    description: str = ("Create notes. Searches using ares_tool and summarizes top relevant note from YouTube or stored data.")
    arg: str = "A question or topic like 'explain transformers'"
    def __init__(self, vector_db: Any, embedding_model: Any, youtube_tool: Any, ares_tool: Any):
        super().__init__()
        object.__setattr__(self, "vector_db", vector_db)
        object.__setattr__(self, "embedding_model", embedding_model)
        object.__setattr__(self, "youtube_tool", youtube_tool)
        object.__setattr__(self, "ares_tool", ares_tool)
    def run(self, prompt: str) -> str:
        if not prompt.strip(): return "Please enter a valid query."
        print("FAISS index ntotal:", self.vector_db.index.ntotal)
        query_embedding = self.embed(prompt)
        results = self.vector_db.similarity_search(query_embedding, k=1)
        if not results:
            result = self.ingest_youtube_notes(prompt)
            return f"No matching notes found. Ingested from YouTube. {result}. Call again to summarize."
        top_note = results[0]["text"]
        try:
            summary = self.ares_tool.run(top_note)
            return f"[FINALIZED NOTES]\n{summary}"
        except Exception as e: return f"Found a note but summarization failed: {e}"
    def embed(self, text: str) -> List[float]:
        return self.embedding_model.encode(text, normalize_embeddings=True).tolist()
    def ingest_youtube_notes(self, query: str) -> str:
        try:
            print(f"🔎 Fetching YouTube content for query: {query}")
            result = self.youtube_tool.run(query)
            if isinstance(result, str) and result.strip():
                self.vector_db.note_store.append({"text": result})
                video_embedding = self.embedding_model.encode([result], normalize_embeddings=True)
                self.vector_db.index.add(np.array(video_embedding).astype("float32"))
                return " YouTube content ingested successfully."
            return " Unexpected YouTube result format."
        except Exception as e: return f" Error during ingestion: {e}"
