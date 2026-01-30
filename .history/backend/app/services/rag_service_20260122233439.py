"""
RAG Service
Handles vector embeddings, semantic search, and AI chat responses
"""
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMADB_AVAILABLE = True
except Exception:
    chromadb = None
    ChromaSettings = None
    _CHROMADB_AVAILABLE = False
from sqlalchemy.orm import Session
from typing import List, Optional
import re

from ..config import get_settings
from ..models import Video

settings = get_settings()

# Initialize ChromaDB lazily (allow server to start without chromadb installed)
if _CHROMADB_AVAILABLE:
    chroma_client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False)
    )

    # Get or create collection
    collection = chroma_client.get_or_create_collection(
        name="video_chunks",
        metadata={"hnsw:space": "cosine"}
    )
else:
    chroma_client = None
    collection = None


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[dict]:
    """Split text into overlapping chunks with approximate timestamps"""
    words = text.split()
    chunks = []
    
    # Estimate words per second (average speaking rate ~150 wpm = 2.5 wps)
    words_per_second = 2.5
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)
        
        # Estimate timestamps
        start_time = int(i / words_per_second)
        end_time = int((i + len(chunk_words)) / words_per_second)
        
        chunks.append({
            "text": chunk_text,
            "start": start_time,
            "end": end_time,
            "index": len(chunks)
        })
    
    return chunks


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings for texts using Google or OpenAI"""
    # Check for valid Google API key (prioritize Google)
    if settings.google_api_key and not settings.google_api_key.startswith('your-'):
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        
        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text
            )
            embeddings.append(result['embedding'])
        return embeddings
    
    # Fallback to OpenAI if valid key exists
    elif settings.openai_api_key and not settings.openai_api_key.startswith('your-'):
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)
        
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        return [e.embedding for e in response.data]
    
    else:
        raise Exception("No valid AI API key configured. Please add GOOGLE_API_KEY or OPENAI_API_KEY to .env")


async def add_video_to_index(video_id: str, transcript: str):
    """Add video transcript chunks to vector index"""
    chunks = chunk_text(transcript)
    
    if not chunks:
        return
    
    # Get embeddings
    texts = [c["text"] for c in chunks]
    embeddings = await get_embeddings(texts)

    # Add to ChromaDB if available
    if collection is None:
        raise RuntimeError("ChromaDB is not available in this environment")

    collection.add(
        ids=[f"{video_id}_{c['index']}" for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{
            "video_id": video_id,
            "start": c["start"],
            "end": c["end"]
        } for c in chunks]
    )


async def search_similar_chunks(query: str, video_id: Optional[str] = None, limit: int = 5) -> List[dict]:
    """Search for similar chunks in vector database"""
    # Get query embedding
    query_embedding = (await get_embeddings([query]))[0]
    
    # Build where filter
    where_filter = {"video_id": video_id} if video_id else None
    
    if collection is None:
        raise RuntimeError("ChromaDB is not available in this environment")

    # Search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )
    
    chunks = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "text": doc,
                "video_id": results["metadatas"][0][i]["video_id"],
                "start": results["metadatas"][0][i]["start"],
                "end": results["metadatas"][0][i]["end"],
                "score": 1 - results["distances"][0][i]  # Convert distance to similarity
            })
    
    return chunks


async def get_rag_response(video_id: str, question: str, db: Session) -> dict:
    """Get AI response using RAG (Retrieval Augmented Generation)"""
    # Get relevant chunks
    chunks = await search_similar_chunks(question, video_id, limit=5)
    
    # Build context
    context = "\n\n".join([
        f"[{c['start']}s - {c['end']}s]: {c['text']}"
        for c in chunks
    ])
    
    # Get video info
    video = db.query(Video).filter(Video.id == video_id).first()
    video_title = video.title if video else "Unknown"
    
    # Build prompt
    system_prompt = f"""You are an AI assistant helping users understand the video "{video_title}".
Use the following transcript excerpts to answer the user's question.
Always cite the relevant timestamps when referencing content.
If the answer isn't in the provided context, say so.

Context from video transcript:
{context}"""

    # Generate response
    response_text = await generate_llm_response(system_prompt, question)
    
    # Extract timestamp references
    references = []
    for chunk in chunks[:3]:  # Top 3 relevant chunks
        references.append({
            "start": chunk["start"],
            "end": chunk["end"],
            "text": chunk["text"][:100] + "..."
        })
    
    return {
        "message": response_text,
        "references": references
    }


async def generate_llm_response(system_prompt: str, user_message: str) -> str:
    """Generate response using configured LLM"""
    # Prioritize Google Gemini
    if settings.google_api_key and not settings.google_api_key.startswith('your-'):
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(f"{system_prompt}\n\nUser: {user_message}")
        return response.text
    
    # Fallback to OpenAI
    elif settings.openai_api_key and not settings.openai_api_key.startswith('your-'):
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    
    else:
        raise Exception("No valid LLM API key configured")


async def search_videos(query: str, video_id: Optional[str], limit: int, db: Session) -> List[dict]:
    """Search across all videos"""
    chunks = await search_similar_chunks(query, video_id, limit)
    
    results = []
    for chunk in chunks:
        video = db.query(Video).filter(Video.id == chunk["video_id"]).first()
        results.append({
            "video_id": chunk["video_id"],
            "video_title": video.title if video else "Unknown",
            "text": chunk["text"],
            "timestamp_start": chunk["start"],
            "timestamp_end": chunk["end"],
            "relevance_score": chunk["score"]
        })
    
    return results
