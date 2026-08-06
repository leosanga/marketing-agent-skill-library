"""Dependency-free embeddings.

chromadb's DefaultEmbeddingFunction lazily imports onnxruntime and loads MiniLM
on the first embed call, which blows past Render's 512MB free-tier limit. This
replaces it with stdlib feature hashing ("hashing trick"): good enough for a few
hundred short, structured marketing records, and costs ~0 memory.
"""

import hashlib
import math
import re
from typing import Any, Dict

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

# 256 buckets: ample for this dataset's few-hundred-word vocabulary, collisions negligible.
DIM = 256

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def embed_text(text: str) -> list[float]:
    """Signed bag-of-words hashed into DIM buckets, L2-normalized."""
    vector = [0.0] * DIM
    for token in _TOKEN_RE.findall(text.lower()):
        digest = int.from_bytes(
            hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big"
        )
        # Low bits pick the bucket, a higher bit picks the sign so collisions cancel
        # instead of always reinforcing.
        vector[digest % DIM] += 1.0 if (digest >> 16) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


class HashingEmbeddingFunction(EmbeddingFunction[Documents]):
    """Drop-in replacement for DefaultEmbeddingFunction with no ML runtime."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [embed_text(doc) for doc in input]

    @staticmethod
    def name() -> str:
        return "stdlib_hashing"

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "HashingEmbeddingFunction":
        return HashingEmbeddingFunction()

    def get_config(self) -> Dict[str, Any]:
        return {}
