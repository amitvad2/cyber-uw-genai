import os
import numpy as np
from google import genai
from google.cloud import firestore, storage

PROJECT  = os.environ.get("GOOGLE_CLOUD_PROJECT", "bt-mvp-dev-eu")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west2")
FIRESTORE_DB = os.environ.get("FIRESTORE_DB", "uw-demo")
GEN_MODEL = os.environ.get("GEN_MODEL", "gemini-3.5-flash")
EMB_MODEL = os.environ.get("EMB_MODEL", "text-embedding-005")

genai_client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
db  = firestore.Client(project=PROJECT, database=FIRESTORE_DB)  # named DB, not (default)
gcs = storage.Client(project=PROJECT)

GUIDELINES = """MFA must be enforced on ALL remote access, email, and privileged admin accounts.
Backups must be offline/immutable and restore-tested within the last 12 months.
EDR must be deployed on 100% of endpoints including servers.
No end-of-life operating systems permitted in production.
An incident response plan must exist and be tested within the last 12 months.
A formal third-party/vendor security assessment process must be in place."""


def embed(texts):
    resp = genai_client.models.embed_content(model=EMB_MODEL, contents=texts)
    return [list(e.values) for e in resp.embeddings]


def chunk_text(text, max_chars=1100, overlap_sentences=1):
    """Structure-aware chunking.

    Splits on natural boundaries (blank lines -> paragraphs, then sentences) and packs
    whole sentences into chunks up to max_chars, so a control sentence is never cut
    mid-clause. Carries `overlap_sentences` from the end of one chunk into the next so a
    fact sitting on a boundary survives in both. Falls back to a hard character cut only
    if a single sentence somehow exceeds max_chars.
    """
    import re
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    sentences = []
    for p in paras:
        for s in re.split(r"(?<=[.!?])\s+", p):
            s = s.strip()
            if not s:
                continue
            if len(s) <= max_chars:
                sentences.append(s)
            else:  # pathological long sentence -> hard slice
                for i in range(0, len(s), max_chars):
                    sentences.append(s[i:i + max_chars])

    chunks, cur, cur_len = [], [], 0
    for s in sentences:
        if cur and cur_len + len(s) + 1 > max_chars:
            chunks.append(" ".join(cur))
            cur = cur[-overlap_sentences:] if overlap_sentences else []
            cur_len = sum(len(x) + 1 for x in cur)
        cur.append(s)
        cur_len += len(s) + 1
    if cur:
        chunks.append(" ".join(cur))
    return [c.strip() for c in chunks if c.strip()]


def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))