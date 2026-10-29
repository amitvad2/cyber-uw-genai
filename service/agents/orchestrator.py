"""Orchestrator: fan-out to specialists (in parallel), fan-in to one aggregated assessment.

This is the multi-agent layer. The fan-out is parallelism; the AGENCY lives inside each
specialist's loop (specialist_plain.run_specialist). The orchestrator then aggregates the
independent findings into one assessment for the human underwriter.
"""
import concurrent.futures as cf
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import common
from agents.specialist_plain import run_specialist

# Each domain = one specialist. Guidelines are multi-part on purpose so the loop can fire.
DOMAINS = {
    "Identity / MFA": {
        "guideline": "MFA must be enforced on ALL of: remote access, email, AND privileged admin accounts.",
        "seed": "multi-factor authentication MFA coverage remote email admin",
    },
    "Backups / Resilience": {
        "guideline": "Backups must be offline/immutable AND restore-tested within the last 12 months.",
        "seed": "backup immutability restore testing frequency",
    },
    "Endpoint": {
        "guideline": "EDR on 100% of endpoints incl. servers; no end-of-life operating systems in production.",
        "seed": "EDR endpoint coverage servers end of life operating system patching",
    },
    "Third-party": {
        "guideline": "A formal third-party/vendor security assessment process must be in place.",
        "seed": "third party vendor supply chain security assessment",
    },
}


def run_orchestrator(submission_id: str) -> dict:
    """Run all specialists in parallel, then aggregate their findings."""
    findings = []
    with cf.ThreadPoolExecutor(max_workers=len(DOMAINS)) as pool:
        futures = {
            pool.submit(run_specialist, submission_id, d, cfg["guideline"], cfg["seed"]): d
            for d, cfg in DOMAINS.items()
        }
        for fut in cf.as_completed(futures):
            findings.append(fut.result())

    joined = "\n\n".join(f"### {f['domain']} (took {f['loops']} loop(s))\n{f['finding']}"
                         for f in findings)
    summary = common.genai_client.models.generate_content(
        model=common.GEN_MODEL,
        contents=f"""You are the lead underwriting assistant. Combine the specialist findings below
into a single overall assessment: a one-line verdict, then the per-domain MET/NOT MET list.
Do NOT make the final decision - this is for a human underwriter.

SPECIALIST FINDINGS:
{joined}""").text

    return {
        "submission_id": submission_id,
        "assessment": summary,
        "specialist_findings": findings,  # includes each loop trace for the demo
    }
