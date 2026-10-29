"""Shared retrieval tool. Used by BOTH the plain loop and the ADK agents.

This is the single 'tool' the agents call. It performs semantic retrieval over the
submission's chunks in Firestore. Exposing retrieval as a callable tool (rather than
hard-wiring it into one step) is what lets an agent decide WHEN and WITH WHAT QUERY to
retrieve again.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import common


def retrieve(submission_id: str, query: str, top_k: int = 4) -> list[dict]:
    """Retrieve the most relevant evidence chunks for a query.

    Args:
        submission_id: the submission to search within.
        query: the natural-language search query.
        top_k: how many chunks to return.
    Returns:
        A list of {page, text, score} dicts, best first.
    """
    col = common.db.collection("submissions").document(submission_id).collection("chunks")
    chunks = [d.to_dict() for d in col.stream()]
    if not chunks:
        return []
    qv = common.embed([query])[0]
    scored = [
        {"page": c["page"], "text": c["text"], "score": round(common.cosine(qv, c["emb"]), 3)}
        for c in chunks
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
