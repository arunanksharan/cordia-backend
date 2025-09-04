import hashlib
import math
from app.platform.ports.embeddings import EmbeddingsPort

class HashingEmbeddings(EmbeddingsPort):
    """
    Deterministic, lightweight embeddings via feature hashing.
    Not semantically strong, but production-safe and swappable.
    """
    def __init__(self, d: int = 384):
        self._d = int(d)

    def dim(self) -> int:
        return self._d

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            v = [0.0] * self._d
            for tok in self._tokenize(t):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                idx = h % self._d
                v[idx] += 1.0
            self._l2_normalize(v)
            out.append(v)
        return out

    def _tokenize(self, text: str) -> list[str]:
        # simple lowercase + split on non-alnum
        import re
        return [x for x in re.split(r"[^a-z0-9]+", (text or "").lower()) if x]

    def _l2_normalize(self, v: list[float]) -> None:
        s = math.sqrt(sum(x*x for x in v)) or 1.0
        for i in range(len(v)):
            v[i] /= s