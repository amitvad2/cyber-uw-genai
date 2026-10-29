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

def chunk_text(text, size=700, overlap=120):
    out, i = [], 0
    while i < len(text):
        piece = text[i:i + size].strip()
        if piece:
            out.append(piece)
        i += size - overlap
    return out

def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
