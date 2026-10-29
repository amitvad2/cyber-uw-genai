import io, sys
from pypdf import PdfReader
import common

path = sys.argv[1]; sub_id = sys.argv[2]
reader = PdfReader(path)
recs = []
for n, pg in enumerate(reader.pages, 1):
    txt = pg.extract_text() or ""
    for ch in common.chunk_text(txt):
        recs.append({"page": n, "text": ch})
print(f"{len(recs)} chunks; embedding...")
embs = common.embed([r["text"] for r in recs])
col = common.db.collection("submissions").document(sub_id).collection("chunks")
B = 400
for i in range(0, len(recs), B):
    batch = common.db.batch()
    for j, (r, e) in enumerate(zip(recs[i:i+B], embs[i:i+B])):
        batch.set(col.document(f"c{i+j}"), {"page": r["page"], "text": r["text"], "emb": e})
    batch.commit()
common.db.collection("submissions").document(sub_id).set(
    {"status": "indexed", "n_chunks": len(recs)}, merge=True)
print("indexed as", sub_id)
