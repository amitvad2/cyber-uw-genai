<<<<<<< HEAD
# Cyber Underwriting GenAI — Event-Driven RAG on GCP (Terraform + GitHub Actions)

A hardened, event-driven Retrieval-Augmented Generation pipeline that triages cyber
insurance submissions. A broker PDF lands in Cloud Storage; the system extracts, indexes
and evaluates it against an underwriting rulebook, returning an **evidence-cited
assessment** — the underwriter keeps the decision.

Everything is **Infrastructure-as-Code (Terraform)**, state lives in **GCS**, and the app
ships via **GitHub Actions** using **Workload Identity Federation** (keyless — no SA keys
in the repo).

## Architecture

```
Broker PDF ─▶ GCS bucket ─(object.finalized)─▶ Eventarc ─▶ Cloud Workflows
                                                                │
                            ┌───────────────┬───────────────────┤
                            ▼               ▼                   ▼
                       uw-extract        uw-index          uw-evaluate     (Cloud Run ×3,
                            │               │                   │           one shared image)
                            └───────────────┴───────────────────┴─▶ Firestore (uw-demo)
                                            │
                                            └─▶ Vertex AI: text-embedding-005 + gemini-3.5-flash
```

| Layer | Service |
|---|---|
| Intake | Cloud Storage bucket `${project}-uw-intake` |
| Event | Eventarc (`object.v1.finalized`) |
| Orchestration | Cloud Workflows `uw-pipeline` |
| Compute | 3× Cloud Run (`uw-extract`, `uw-index`, `uw-evaluate`), one image, `ROLE` env selects behaviour |
| Data | Firestore `uw-demo` (named DB), Cloud Storage |
| AI | Vertex AI — `text-embedding-005`, `gemini-3.5-flash` |
| Region | `europe-west2` (London — UK data residency) |

## Repo layout

```
bootstrap/     one-time: TF state bucket, Artifact Registry, CI service account, WIF
terraform/     the main stack (APIs, IAM, buckets, Firestore, Cloud Run, Workflow, Eventarc)
service/       FastAPI app (extract/index/evaluate), Dockerfile
workflows/     Cloud Workflows definition (Terraform template)
samples/       generator for a demo submission PDF
.github/       GitHub Actions deploy pipeline (WIF auth)
```

## Prerequisites

- `gcloud`, `terraform >= 1.5`, Python 3 (for the sample generator)
- A GCP project with billing and Vertex AI access (this repo assumes `bt-mvp-dev-eu`)
- You are authenticated: `gcloud auth application-default login`

## 1. Bootstrap (run once, local state)

Creates the remote-state bucket, Artifact Registry, the CI service account, and the
Workload Identity Federation pool/provider for GitHub Actions.

```bash
cd bootstrap
terraform init
terraform apply -var="github_repo=YOUR_GH_OWNER/cyber-uw-genai"
terraform output   # note wif_provider and ci_service_account for GitHub
```

Then in your GitHub repo set **Settings → Secrets and variables → Actions → Variables**:

- `WIF_PROVIDER`  = the `wif_provider` output
- `CI_SERVICE_ACCOUNT` = the `ci_service_account` output

## 2a. Deploy from your laptop (Terraform does everything)

```bash
cd terraform
terraform init           # uses the GCS backend created in bootstrap
terraform apply          # builds the image via Cloud Build, then provisions everything
```

## 2b. Deploy via GitHub Actions (CI/CD)

Push to `main`. The pipeline authenticates with WIF, builds the image with Cloud Build,
and runs `terraform apply`. No keys anywhere.

## 3. Run the demo

```bash
make sample              # generates a submission PDF and uploads it to the intake bucket
make test                # shows the workflow execution that fired automatically
```

Read the result:

```bash
python3 - <<'PY'
from google.cloud import firestore
db = firestore.Client(project="bt-mvp-dev-eu", database="uw-demo")
d = db.collection("submissions").document("sample_submission").get().to_dict()
print("STATUS:", d.get("status"), "| CHUNKS:", d.get("n_chunks"))
print("\n", d.get("assessment"))
PY
```

## Design decisions (interview talking points)

- **3 services, 1 image:** independent scaling/IAM/deploy cadence (evaluate is expensive +
  calls Gemini; extract is cheap I/O) without triplicate boilerplate.
- **Keyless CI (WIF):** no service-account JSON keys in the repo or GitHub — short-lived
  federated tokens only.
- **Named Firestore DB:** `uw-demo` isolates demo state from the project's `(default)` DB.
- **In-memory cosine retrieval:** deliberate simplicity; chunks+embeddings persist in
  Firestore. Production swap = Vertex AI Vector Search, same RAG pattern.
- **`europe-west2`:** UK data residency; also why Gemini 404s in US regions on this project.
- **Grounding + control boundary:** AI returns a cited assessment, never the decision.

## Known caveats (honest)

- The Terraform/Workflows/Eventarc here is written to current provider conventions but
  hasn't been `apply`-tested end to end in this environment — expect to pin the google
  provider version and possibly add the Eventarc service-agent grant on first run.
- Eventarc→Workflows can need the Eventarc service agent; if the trigger errors on first
  create, run `gcloud beta services identity create --service=eventarc.googleapis.com`.
- Model names roll forward; if a `404` appears, re-query the publisher catalog and update
  `gen_model` / `emb_model`.

## Teardown

```bash
cd terraform && terraform destroy
# bootstrap resources (state bucket, WIF) can be left or destroyed separately
```

---

## Multi-agent evaluation (added)

The `evaluate` service now supports three strategies via the `EVAL_MODE` env var:

| `EVAL_MODE` | What runs | When to use |
|---|---|---|
| `plain` (default) | Framework-free multi-agent orchestrator — a reason→act→observe loop per specialist | The runnable, explain-every-line version |
| `adk` | Same design on Vertex AI ADK (`LlmAgent` + `ParallelAgent`) | The on-platform framework framing |
| `simple` | Original single-pass RAG | Baseline for comparison |

### Where the agency actually is
The fan-out across specialists (`agents/orchestrator.py`) is just **parallelism**. The
**agentic loop** lives inside each specialist (`agents/specialist_plain.py`): it retrieves,
the model judges whether the evidence covers every part of a multi-part guideline, and if a
part is neither confirmed nor contradicted it generates a **new, more specific query and
loops** (capped at `MAX_LOOPS`). That "decide the next query from what I just saw" step is
what makes it an agent, not parallel RAG.

### Why you need a big submission to see it loop
On a 1-page sample, one retrieval returns everything and the loop exits after one pass —
correct, but undemonstrative. Use `samples/make_rich_sample.py` to generate a 100-page
submission where controls are scattered far apart (MFA remote on p.6, admin exclusion on
p.78) and use applicant vocabulary that differs from the rulebook ("WORM retention lock"
vs "immutable"). Those two conditions — multi-part rules beyond top-k, and vocabulary
mismatch — force the specialists to re-query. `loops_per_domain` is written to Firestore so
you can show which domains needed more than one pass.

```bash
cd samples && python3 make_rich_sample.py
gcloud storage cp rich_submission.pdf gs://bt-mvp-dev-eu-uw-intake/
```

### Honest status
- `agents/specialist_plain.py` + `agents/orchestrator.py` are compile-checked and follow
  the same proven retrieval you already ran — this is the version to demo.
- `agents/adk_agents.py` is written to current `google-adk` patterns but was **not executed
  here** (no network/GCP in the build env). Verify the `Runner`/session API against your
  installed `google-adk` on first run; the `LlmAgent`/tool definitions are the stable part.
- Judgment point for the interview: agents are applied **only at evaluation**, where
  open-ended reasoning over scattered evidence pays off. Extract and index stay
  deterministic. Single-part rules don't need a loop — don't pay for one where a single
  pass suffices.
=======
# cyber-uw-genai
Repo for UW Cyber specialist GenAI Assistant
>>>>>>> 3b24aed9ce66d2531c250f3acc2aa6a39c9acda1
