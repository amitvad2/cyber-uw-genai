"""Framework-free specialist agent: a real reason -> act -> observe -> decide loop.

This is the version you can explain line by line. Each specialist owns ONE control
domain. It retrieves, then the model DECIDES whether the evidence is sufficient for a
multi-part rule; if not, it proposes the next query and loops. The loop is what makes it
an agent rather than a single RAG pass.
"""
import json
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import common
from agents.retrieval_tool import retrieve

MAX_LOOPS = 3  # cap so a confused agent can't loop forever (a real production guardrail)


def _ask_json(prompt: str) -> dict:
    """Call the model and parse a JSON object from its reply (tolerates code fences)."""
    resp = common.genai_client.models.generate_content(
        model=common.GEN_MODEL, contents=prompt)
    text = resp.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        return {"sufficient": True, "reason": "parse fallback", "next_query": ""}


def run_specialist(submission_id: str, domain: str, guideline: str, seed_query: str) -> dict:
    """Run one specialist's reason/act/observe loop over its domain."""
    gathered, trace, query, seen = [], [], seed_query, set()

    for step in range(1, MAX_LOOPS + 1):
        # ACT: retrieve for the current query
        hits = retrieve(submission_id, query, top_k=4)
        for h in hits:
            key = (h["page"], h["text"][:40])
            if key not in seen:
                seen.add(key); gathered.append(h)

        # OBSERVE + REASON: is what we have enough for this (possibly multi-part) rule?
        evidence = "\n".join(f"- (p.{h['page']}) {h['text'][:300]}" for h in gathered)
        decision = _ask_json(f"""You are the {domain} control specialist for a cyber underwriter.
GUIDELINE (may have several parts):
{guideline}

EVIDENCE GATHERED SO FAR:
{evidence if evidence else "(nothing yet)"}

Decide if the evidence is SUFFICIENT to assess EVERY part of the guideline. If a part is
neither confirmed nor contradicted, it is NOT sufficient - you must look again with a
different, more specific query. Reply ONLY with JSON:
{{"sufficient": true|false, "reason": "...", "next_query": "a better search query or empty"}}""")

        trace.append({"step": step, "query": query,
                      "found": len(hits), "reason": decision.get("reason", "")})

        if decision.get("sufficient") or not decision.get("next_query"):
            break
        query = decision["next_query"]  # REASON drives the next ACT

    # Conclude from everything gathered
    evidence = "\n".join(f"[{i+1}] (p.{h['page']}) {h['text'][:300]}"
                         for i, h in enumerate(gathered))
    final = common.genai_client.models.generate_content(
        model=common.GEN_MODEL,
        contents=f"""You are the {domain} specialist. Using ONLY the evidence below, assess the
guideline. Mark MET / NOT MET / UNCLEAR with a one-line reason and [citation].

GUIDELINE:
{guideline}

EVIDENCE:
{evidence}""").text

    return {"domain": domain, "finding": final, "loops": len(trace), "trace": trace}
