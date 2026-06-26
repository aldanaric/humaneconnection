import csv
import io
import numpy as np
import os
import tiktoken as tkn
from PIL import Image
from PyPDF2 import PdfReader
from openai import OpenAI
from pdf2image import convert_from_path
from sklearn.neighbors import NearestNeighbors
from typing import List, Tuple

# Global configuration
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI's best embeddings as of Feb 2024
CSV_FILE_PATH = "data/HumaneConnection.embeddings.csv"

async def ask_book(query: str, return_image: bool = False):
    """
    Main RAG (Retrieval Augmented Generation) implementation.
    Takes a query about the book and returns relevant information with optional page image.

    Returns:
    {
        "answer": str,           # Generated response using context
        "page_number": int,      # Page where context was found
        "context": str,          # Text chunk used for answer
        "image_data": bytes      # Optional PNG of page if return_image=True
    }
    """

    # Source PDF path
    pdf_path = "data/HumaneConnection.pdf"

    # --- Embedding management ---
    # 1. Check if embeddings exist in CSV_FILE_PATH
    if not os.path.exists(CSV_FILE_PATH):
        # 2. Embeddings don't exist — generate and save them
        # Extract text from PDF
        pages_text = __extract_text_from_pdf(pdf_path)

        # Chunk the text
        chunks = __chunk_prompt(pages_text)

        # Separate page numbers and text for embedding
        chunk_page_numbers = [page_num for page_num, _ in chunks]
        chunk_texts = [text for _, text in chunks]

        # Calculate embeddings using local model
        embeddings = await __calculate_embeddings(chunk_texts)

        # Determine document name from PDF path
        document_name = os.path.basename(pdf_path)

        # Save to CSV for future use
        save_embeddings_to_csv(
            file_path=CSV_FILE_PATH,
            document_name=document_name,
            page_numbers=chunk_page_numbers,
            embeddings=embeddings,
            contexts=chunk_texts
        )

    # 3. Load embeddings from CSV
    records = load_embeddings_from_csv(CSV_FILE_PATH)

    # --- Semantic search ---
    # 1. Set up nearest neighbors search with sklearn (cosine similarity)
    if not records:
        raise RuntimeError(f"No embeddings loaded from {CSV_FILE_PATH}")

    top_k = 3

    embedding_matrix = np.array(
        [record["embedding"] for record in records],
        dtype=np.float32
    )
    nn_model = NearestNeighbors(n_neighbors=top_k, metric="cosine")
    nn_model.fit(embedding_matrix)

    # 2. Get embedding for user's query
    local_embedder = LocalEmbeddingGenerator()
    query_embedding = local_embedder.generate_single_embedding(query)
    query_vector = np.array(query_embedding, dtype=np.float32).reshape(1, -1)

    # 3. Find most relevant contexts using cosine similarity
    distances, indices = nn_model.kneighbors(query_vector)

    top_records = [records[i] for i in indices[0]]
    best_record = top_records[0]

    # Use the first/best chunk as the displayed reference
    context = best_record["context"]
    page_number = best_record["page_number"]

    # Combine top chunks for the LLM context
    combined_context = "\n\n---\n\n".join(
        [
            f"Page {record['page_number']}:\n{record['context']}"
            for record in top_records
        ]
    )

    # --- Answer generation ---
    # 1. Format prompt with context and query
    prompt = (
        f"You are an expert assistant for the 'The Humane Connection'.\n"
        f"Use the following excerpts from the book to answer the user's question.\n\n"
        f"Book excerpts:\n{combined_context}\n\n"
        f"User question: {query}\n\n"
        f"Provide a clear, helpful answer based on the excerpts above."
    )

    # 2. Get response from LLM using converse_sync
    from services.llm import converse_sync
    answer, _ = converse_sync(prompt=prompt, messages=[])

    # 3. Package results
    result = {
        "answer": answer,
        "page_number": page_number,
        "context": context,
    }

    # --- Optional: Handle page image extraction ---
    if return_image:
        try:
            image_data = __extract_page_as_image(pdf_path, page_number)
        except RuntimeError as e:
            print(f"RAG image generation skipped: {e}")
            image_data = b""
        result["image_data"] = image_data

    return result

def __extract_text_from_pdf(pdf_path: str) -> List[Tuple[int, str]]:
    """
    Extract text content from each page of the PDF.
    Returns: List of (page_number, page_text) tuples
    """
    pages_text = []
    with open(pdf_path, "rb") as f:
        reader = PdfReader(f)
        num_pages = len(reader.pages)
        for page_index in range(num_pages):
            page = reader.pages[page_index]
            text = page.extract_text() or ""
            # page_number is 1-based
            pages_text.append((page_index + 1, text))
    return pages_text

def __extract_page_as_image(pdf_path: str, page_number: int) -> bytes:
    """
    Convert a specific PDF page to a PNG image.
    Returns: Raw PNG image data as bytes
    """
    # pdf2image uses 1-based page numbers via first_page/last_page
    try:
        images = convert_from_path(
            pdf_path,
            first_page=page_number,
            last_page=page_number,
            dpi=150
        )
    except Exception as e:
        raise RuntimeError(
            "Unable to render PDF page image. "
            "Make sure Poppler is installed and available in PATH. "
            f"Original error: {e}"
        )

    if not images:
        return b""
    img = images[0]
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

async def __chunk_prompt(
    pages_text: List[Tuple[int, str]],
    chunk_size: int = 1500,
    overlap: int = 50
) -> List[Tuple[int, str]]:
    """
    Split text into chunks suitable for embedding.

    For this project, keep one primary chunk per page, but add light overlap
    from the previous and next pages to preserve context continuity.

    The returned page_number is still the primary page used for evidence display.
    """
    encoding = tkn.get_encoding("cl100k_base")
    chunks = []

    for i, (page_number, text) in enumerate(pages_text):
        center_text = text.strip()
        if not center_text:
            continue

        parts = []

        # Add trailing overlap from previous page
        if i > 0:
            prev_text = pages_text[i - 1][1].strip()
            if prev_text:
                prev_tokens = encoding.encode(prev_text)
                prev_overlap_text = encoding.decode(prev_tokens[-overlap:]) if len(prev_tokens) > overlap else prev_text
                parts.append(prev_overlap_text)

        # Add full current page
        parts.append(center_text)

        # Add leading overlap from next page
        if i < len(pages_text) - 1:
            next_text = pages_text[i + 1][1].strip()
            if next_text:
                next_tokens = encoding.encode(next_text)
                next_overlap_text = encoding.decode(next_tokens[:overlap]) if len(next_tokens) > overlap else next_text
                parts.append(next_overlap_text)

        chunk_text = "\n\n".join(parts).strip()
        chunks.append((page_number, chunk_text))

    return chunks

# TODO: Use this local embedding generator to embed text without network API calls
LOCAL_EMBEDDING_MODEL = "all-mpnet-base-v2"  # Better accuracy local model (~420MB)
class LocalEmbeddingGenerator():
    """Local embedding generator using sentence-transformers."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        self._dimension = None

    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"Loading local embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name, device="cpu")
                # Test embedding to get dimension
                test_embedding = self._model.encode(["test"], normalize_embeddings=True)
                self._dimension = test_embedding.shape[1]
                print(f"Local embedding model loaded. Dimension: {self._dimension}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for local embeddings. Install with: pip install sentence-transformers")
            except Exception as e:
                raise RuntimeError(f"Failed to load local embedding model {self.model_name}: {e}")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        self._load_model()
        embeddings = self._model.encode(texts, batch_size=32, normalize_embeddings=True)
        return embeddings.tolist()

    def generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        self._load_model()
        embedding = self._model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

    @property
    def embedding_dimension(self) -> int:
        """Return the dimension of the embeddings."""
        if self._dimension is None:
            self._load_model()
        return self._dimension


async def __calculate_embeddings(documents: List[str], batch_size: int = 20) -> List[List[float]]:
    """
    Get embeddings for text chunks using sentence transformers.

    Hint: Use the local embedding generator above for offline embedding.

    Args:
        documents: List of text chunks to embed
        batch_size: Number of chunks to process at once

    Returns: List of embedding vectors (each vector is List[float])
    """
    generator = LocalEmbeddingGenerator()
    all_embeddings = []

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batch_embeddings = generator.generate_embeddings(batch)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings

def save_embeddings_to_csv(file_path: str, document_name: str, page_numbers: List[int], embeddings: List[List[float]], contexts: List[str]):
    """
    Cache embeddings to CSV for faster future lookups.

    CSV Format:
    document_name, page_number, embedding, context

    Args:
        file_path: Where to save the CSV
        document_name: Identifier for the source document
        page_numbers: List of page numbers for each chunk
        embeddings: List of embedding vectors
        contexts: List of text chunks
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(["document_name", "page_number", "embedding", "context"])
        # Write each record
        for page_number, embedding, context in zip(page_numbers, embeddings, contexts):
            # Serialize embedding as a comma-separated string inside the cell
            embedding_str = str(embedding)
            writer.writerow([document_name, page_number, embedding_str, context])

def load_embeddings_from_csv(file_path: str) -> List[dict]:
    """
    Load previously cached embeddings from CSV.

    Returns: List of dicts with keys:
        - document_name: str
        - page_number: int
        - embedding: List[float]
        - context: str
    """
    import ast

    records = []
    with open(file_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            embedding = ast.literal_eval(row["embedding"])
            records.append({
                "document_name": row["document_name"],
                "page_number": int(row["page_number"]),
                "embedding": embedding,
                "context": row["context"],
            })
    return records
