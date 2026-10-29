import io, os
from fastapi import FastAPI, Request
from pypdf import PdfReader
import common

ROLE = os.environ.get("ROLE", "extract")
app = FastAPI(title=f"uw-{ROLE}")

@app.get("/health")
def health():
    return {"ok": True, "role": ROLE}

@app.post("/")
async def handle(req: Request):
    body = await req.json()
    if ROLE == "extract":
        return do_extract(body)
    if ROLE == "index":
        return do_index(body)
    if ROLE == "evaluate":
        return do_evaluate(body)
    return {"error": f"unknown ROLE {ROLE}"}

def do_extract(body):
    bucket, name = body["bucket"], body["name"]
    sub_id = os.path.splitext(os.path.basename(name))[0].replace(" ", "_")
    data = common.gcs.bucket(bucket).blob(name).download_as_bytes()
    reader = PdfReader(io.BytesIO(data))
    pages = [{"page": n, "text": (p.extract_text() or "")}
             for n, p in enumerate(reader.pages, 1)]
    common.db.collection("submissions").document(sub_id).set(
        {"source": name, "bucket": bucket, "pages": pages, "status": "extracted"})
    return {"submission_id": sub_id, "pages": len(pages)}

def do_index(body):
    sub_id = body["submission_id"]
    doc = common.db.collection("submissions").document(sub_id).get().to_dict()
    recs = [{"page": pg["page"], "text": ch}
            for pg in doc["pages"] for ch in common.chunk_text(pg["text"])]
    embs = common.embed([r["text"] for r in recs])
    col = common.db.collection("submissions").document(sub_id).collection("chunks")
    batch = common.db.batch()
    for i, (r, e) in enumerate(zip(recs, embs)):
        batch.set(col.document(f"c{i}"), {"page": r["page"], "text": r["text"], "emb": e})
    batch.commit()
    common.db.collection("submissions").document(sub_id).update(
        {"status": "indexed", "n_chunks": len(recs)})
    return {"submission_id": sub_id, "n_chunks": len(recs)}

def do_evaluate(body):
    """Evaluate a submission. EVAL_MODE selects the strategy:
       plain  (default) = multi-agent orchestrator, framework-free reason/act/observe loops
       adk               = same design on Vertex AI ADK
       simple            = original single-pass RAG (kept for comparison)
    """
    import os, asyncio
    sub_id = body["submission_id"]
    mode = os.environ.get("EVAL_MODE", "plain")

    if mode == "simple":
        return _evaluate_simple(body)

    if mode == "adk":
        from agents.adk_agents import run_adk
        assessment = asyncio.run(run_adk(sub_id))
        common.db.collection("submissions").document(sub_id).update(
            {"status": "assessed", "assessment": assessment, "eval_mode": "adk"})
        return {"submission_id": sub_id, "assessment": assessment, "eval_mode": "adk"}

    # default: plain multi-agent orchestrator
    from agents.orchestrator import run_orchestrator
    result = run_orchestrator(sub_id)
    common.db.collection("submissions").document(sub_id).update(
        {"status": "assessed", "assessment": result["assessment"],
         "eval_mode": "plain",
         "loops_per_domain": {f["domain"]: f["loops"] for f in result["specialist_findings"]}})
    return result


def _evaluate_simple(body):
    sub_id = body["submission_id"]
    question = body.get("question",
        "Does this risk meet our MFA, backup, EDR, patching, IR and third-party requirements?")
    col = common.db.collection("submissions").document(sub_id).collection("chunks")
    chunks = [d.to_dict() for d in col.stream()]
    qv = common.embed([question])[0]
    hits = sorted(chunks, key=lambda c: common.cosine(qv, c["emb"]), reverse=True)[:4]
    evidence = "\n\n".join(f"[{i+1}] (p.{c['page']}) {c['text']}" for i, c in enumerate(hits))
    prompt = f"""You are assisting a cyber underwriter. Answer ONLY from the evidence and
guidelines below. Cite evidence by its [number]. If evidence is insufficient, say so.
Do NOT make the final underwriting decision - give an evidence-backed assessment.

UNDERWRITING GUIDELINES:
{common.GUIDELINES}

SUBMISSION EVIDENCE:
{evidence}

QUESTION: {question}

Respond with: (1) a one-line overall assessment, then (2) each relevant guideline
marked MET / NOT MET / UNCLEAR with a short reason and a [citation]."""
    resp = common.genai_client.models.generate_content(
        model=common.GEN_MODEL, contents=prompt)
    common.db.collection("submissions").document(sub_id).update(
        {"status": "assessed", "question": question, "assessment": resp.text, "eval_mode": "simple"})
    return {"submission_id": sub_id, "assessment": resp.text, "eval_mode": "simple"}
