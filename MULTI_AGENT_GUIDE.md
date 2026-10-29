# Multi-Agent Evaluation — Step-by-Step Execution Guide

How to run and **demonstrate** the agentic evaluation layer: the reason→act→observe loop
inside each specialist, the fan-out/fan-in orchestrator, and the single-pass-vs-agentic
contrast that proves the loop earns its place.

Confirmed config (from earlier): project `bt-mvp-dev-eu`, region `europe-west2`,
models `gemini-3.5-flash` + `text-embedding-005`, Firestore db `uw-demo`.

---

## 0. Mental model (say this, don't skip it)

- **Fan-out across specialists = parallelism.** Not agency.
- **The agency is the loop INSIDE each specialist:** retrieve → judge if a multi-part rule
  is fully covered → if not, generate a more specific query and loop → conclude.
- The loop only fires when one retrieval is insufficient: multi-part rules scattered beyond
  top-k, or applicant vocabulary ≠ rulebook vocabulary. That's why we need a big submission.
- Agents are applied **only at evaluation**. Extract and index stay deterministic.

---

## 1. Prerequisites

Either of these:
- **Local run (fastest for seeing the loop):** you have the repo unzipped and run everything
  from inside `cyber-uw-genai/service/` (where `common.py`, `app.py`, and `agents/` live together).
- **Deployed run:** the Terraform stack is applied and the three Cloud Run services exist.

> **Folder layout note.** The agent code imports `common` directly (e.g. `import common`
> inside `agents/retrieval_tool.py`). That only resolves when **`service/` is your working
> directory**. So for local runs: `cd` into `service/`, keep all helper scripts there, and
> do NOT copy files up into a flat folder. Run `git` from `cyber-uw-genai/` (where
> `.gitignore` is), never from a parent folder, or you will commit `.venv`/`__pycache__`.

Set up your shell and working directory (adjust the path to where you unzipped the repo):
```bash
cd ~/CYBER-UW-DEMO/cyber-uw-genai/service
source ~/CYBER-UW-DEMO/.venv/bin/activate
export GOOGLE_CLOUD_PROJECT=bt-mvp-dev-eu
export GOOGLE_CLOUD_LOCATION=europe-west2
export FIRESTORE_DB=uw-demo
export GEN_MODEL=gemini-3.5-flash
export EMB_MODEL=text-embedding-005
setopt interactivecomments nonomatch 2>/dev/null || true
```

Confirm imports resolve BEFORE doing anything else (this is the make-or-break check):
```bash
python3 -c "import common, agents.retrieval_tool, agents.orchestrator; print('imports resolve')"
```

Install dependencies:
```bash
pip install google-adk reportlab
```

---

## 2. Build the rich submission (the one that makes the loop fire)

The generator lives in `../samples/`. Run it so the PDF lands in `service/` where the
helper scripts expect it:

```bash
python3 ../samples/make_rich_sample.py
```

Expected: `Wrote rich_submission.pdf (100 pages; controls on pages [6, 41, 44, 61, 78, 90, 96])`.

Why these pages matter: MFA remote access is on p.6 but the admin-account exclusion is on
p.78 (one query can't pull both); backups say "WORM retention lock" not "immutable"
(vocabulary mismatch). Both force a re-query.

---

## 4. Index the big document

You need the 100-page PDF chunked + embedded into Firestore before agents can retrieve.

**Local path** — create this indexer **inside `service/`** (so `import common` resolves) and
run it. It chunks + embeds the PDF into Firestore under a submission id:

```bash
cat > index_local.py << 'PY'
import io, sys
from pypdf import PdfReader
import common
from agents.retrieval_tool import retrieve  # noqa (import proves package resolves)

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
# Firestore batch limit is 500 writes — chunk the commits
B = 400
for i in range(0, len(recs), B):
    batch = common.db.batch()
    for j, (r, e) in enumerate(zip(recs[i:i+B], embs[i:i+B])):
        batch.set(col.document(f"c{i+j}"), {"page": r["page"], "text": r["text"], "emb": e})
    batch.commit()
common.db.collection("submissions").document(sub_id).set(
    {"status": "indexed", "n_chunks": len(recs)}, merge=True)
print("indexed as", sub_id)
PY

python3 index_local.py rich_submission.pdf rich_submission
```

**Deployed path** — just drop the PDF in the bucket and let Eventarc→Workflow do extract+index:
```bash
gcloud storage cp rich_submission.pdf gs://bt-mvp-dev-eu-uw-intake/
gcloud workflows executions list uw-pipeline --location=europe-west2 --limit=1
```

> Note: 100 pages = hundreds of chunks = hundreds of embedding calls. Expect a few seconds
> and a few cents. This is the real cost trade-off you name in the interview.

---

## 5. Run the multi-agent evaluation — and WATCH IT LOOP

**Local path** (best for the demo — you see the trace). Create this **inside `service/`**:

```bash
cat > run_agents.py << 'PY'
import sys, json
from agents.orchestrator import run_orchestrator
res = run_orchestrator(sys.argv[1])
print("\n================ OVERALL ASSESSMENT ================\n")
print(res["assessment"])
print("\n================ PER-SPECIALIST LOOP TRACE ========\n")
for f in res["specialist_findings"]:
    print(f"\n--- {f['domain']}  ({f['loops']} loop(s)) ---")
    for t in f["trace"]:
        print(f"  step {t['step']}: query={t['query']!r}  found={t['found']}")
        print(f"           reason: {t['reason']}")
PY

python3 run_agents.py rich_submission
```

What to look for: domains whose rule is multi-part or whose evidence used different words
should show **2+ loops**, with the step-2 query being more specific than step-1 (e.g. the
MFA specialist re-querying for "privileged admin account authentication" after step 1 only
found remote access). That is the agent deciding its next action from what it observed.

**Deployed path** (sets strategy by env var on the service):
```bash
gcloud run services update uw-evaluate --region=europe-west2 --set-env-vars EVAL_MODE=plain
# then re-run the workflow (or call the service) and read the result in step 7
```

---

## 6. Prove it matters: single-pass vs agentic on the SAME document

This contrast is the most convincing thing you can show. Create it **inside `service/`**:

```bash
cat > compare.py << 'PY'
import sys
sub = sys.argv[1]
# simple single-pass
import app, os
os.environ["EVAL_MODE"] = "simple"
simple = app.do_evaluate({"submission_id": sub})
print("\n########## SIMPLE (single-pass RAG) ##########\n")
print(simple["assessment"])
# agentic
from agents.orchestrator import run_orchestrator
agentic = run_orchestrator(sub)
print("\n########## AGENTIC (multi-agent loop) ##########\n")
print(agentic["assessment"])
print("\nloops:", {f["domain"]: f["loops"] for f in agentic["specialist_findings"]})
PY

python3 compare.py rich_submission
```

Expected story: the single-pass version misses the page-78 admin-MFA exclusion or the
page-41 WORM/immutability equivalence (its one query didn't reach them), so it under-calls
a NOT MET. The agentic version catches it by re-querying. Same document, better coverage —
because of the loop.

---

## 7. Read the stored result (deployed path)

```bash
python3 - <<'PY'
from google.cloud import firestore
db = firestore.Client(project="bt-mvp-dev-eu", database="uw-demo")
d = db.collection("submissions").document("rich_submission").get().to_dict()
print("status:", d.get("status"), "| mode:", d.get("eval_mode"))
print("loops per domain:", d.get("loops_per_domain"))
print("\n", d.get("assessment"))
PY
```

---

## 8. (Optional) Run the ADK version

```bash
gcloud run services update uw-evaluate --region=europe-west2 --set-env-vars EVAL_MODE=adk
```
or locally:
```bash
python3 -c "import asyncio; from agents.adk_agents import run_adk; print(asyncio.run(run_adk('rich_submission')))"
```
> `adk_agents.py` follows current `google-adk` patterns but was not executed when the repo
> was built. If the `Runner`/session call errors, check the installed `google-adk` quickstart
> and adjust the `run_adk` invocation only — the `LlmAgent`/tool definitions are stable.
> The `plain` orchestrator is the guaranteed-runnable equivalent.

---

## 9. Demo narration (what to click + say)

1. Show `make_rich_sample.py` page map → "controls are scattered and worded like a real
   applicant, not like our rulebook."
2. Run `run_agents.py` → point at a domain with 2 loops → "step 1 found remote-access MFA;
   the agent reasoned a part was still unproven and **re-queried** for admin accounts — that
   second query is the agency."
3. Run `compare.py` → "single-pass missed it; the loop caught it. Same document."
4. "Fan-out is parallelism; the loop inside each specialist is the agent. And they only
   assess — the underwriter decides."

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: agents` or `common` | not running from inside `service/` | `cd .../cyber-uw-genai/service` first; run all helper scripts from there |
| `ModuleNotFoundError: google.adk` | ADK not installed | `pip install google-adk` (only needed for `EVAL_MODE=adk`) |
| Loop always exits after 1 pass | document too small / single-part rules | use `rich_submission.pdf`; it's built to force re-queries |
| Firestore batch error on index | >500 writes in one batch | the indexer commits in batches of 400 (already handled) |
| Model `404` | model name rolled forward | update `GEN_MODEL`/`EMB_MODEL` (re-query the catalog) |
| ADK `Runner` error | ADK runtime API drift | use `EVAL_MODE=plain`; verify ADK quickstart for the current runner call |

---

## 11. Interview one-liners

- "The fan-out is parallel RAG; the agent is the reason→act→observe loop inside each
  specialist that decides its next query from what it just found."
- "I apply agents only where open-ended reasoning pays off — evaluation over scattered
  evidence — and keep extract/index deterministic."
- "The loop is insurance against multi-part rules beyond top-k and vocabulary mismatch; on a
  simple single-part question I wouldn't pay for it."
- "Agents assess; the underwriter decides. The control boundary never moves."
