from pathlib import Path
import json

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.app.config import settings


BATCH_SIZE = 32


def load_chunks() -> list[dict]:
    path = Path("backend/data/processed/ts_36_413_chunks.json")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def create_vector_store():
    chunks = load_chunks()

    print(f"Loaded chunks: {len(chunks)}")

    print("Loading embedding model...")
    embedding_model = TextEmbedding(
        model_name=settings.embedding_model
    )

    qdrant_path = Path(settings.qdrant_path)
    qdrant_path.mkdir(parents=True, exist_ok=True)

    client = QdrantClient(path=str(qdrant_path))

    collection_name = settings.qdrant_collection

    # Get embedding dimension from one sample.
    sample_embedding = next(
        embedding_model.embed([chunks[0]["text"]])
    )

    vector_size = len(sample_embedding)

    print(f"Embedding dimension: {vector_size}")

    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )

    total = len(chunks)

    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)

        batch = chunks[start:end]
        texts = [chunk["text"] for chunk in batch]

        print(f"Embedding chunks {start + 1}-{end} of {total}...")

        embeddings = embedding_model.embed(texts)

        points = []

        for chunk, embedding in zip(batch, embeddings):
            points.append(
                PointStruct(
                    id=chunk["chunk_id"],
                    vector=embedding.tolist(),
                    payload={
                        "text": chunk["text"],
                        "section_path": chunk["section_path"],
                        "chunk_id": chunk["chunk_id"],
                        "specification": chunk["specification"],
                        "version": chunk["version"],
                        "release": chunk["release"],
                        "source_file": chunk["source_file"],
                    },
                )
            )

        client.upsert(
            collection_name=collection_name,
            points=points,
        )

        print(f"Stored {end}/{total} chunks.")

    collection = client.get_collection(collection_name)

    print()
    print("Indexing complete.")
    print(f"Vectors stored: {collection.points_count}")

    client.close()


if __name__ == "__main__":
    create_vector_store()