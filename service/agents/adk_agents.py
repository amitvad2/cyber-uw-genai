"""Vertex AI ADK version of the same multi-agent design (the 'on-platform' framing).

NOTE: written to current google-adk patterns but NOT executed in this build environment.
Verify the Runner/session API against the installed google-adk version on first run; the
agent + tool definitions below are the stable part. The plain-Python orchestrator.py is
the guaranteed-runnable equivalent if the ADK runtime API has drifted.

Key idea: an LlmAgent given a tool loops natively - it reasons, calls the tool, observes,
and decides whether to call again before answering. That built-in tool-calling loop IS the
reason->act->observe cycle. ParallelAgent fans the specialists out; a final aggregator
LlmAgent fans them in.
"""
import os
from agents.retrieval_tool import retrieve as _retrieve

MODEL = os.environ.get("GEN_MODEL", "gemini-3.5-flash")

try:
    from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    ADK_AVAILABLE = True
except Exception:
    ADK_AVAILABLE = False


def make_retrieve_tool(submission_id: str):
    """Bind the shared retrieval tool to one submission so agents just pass a query."""
    def search_submission(query: str) -> list[dict]:
        """Search this submission's evidence for text relevant to `query`.
        Call repeatedly with more specific queries until you can assess every part of
        your guideline. Returns a list of {page, text, score}."""
        return _retrieve(submission_id, query, top_k=4)
    return search_submission


def build_root_agent(submission_id: str):
    tool = make_retrieve_tool(submission_id)

    def specialist(name, domain, guideline):
        return LlmAgent(
            name=name, model=MODEL, tools=[tool], output_key=f"{name}_finding",
            instruction=(
                f"You are the {domain} control specialist. Guideline: {guideline}\n"
                "Use search_submission to gather evidence. If any part of the guideline is "
                "neither confirmed nor contradicted, search again with a more specific query "
                "before concluding. Then mark MET / NOT MET / UNCLEAR with [citations]."),
        )

    specialists = [
        specialist("mfa", "Identity/MFA",
                   "MFA enforced on remote access, email AND privileged admin accounts."),
        specialist("backup", "Backups/Resilience",
                   "Backups offline/immutable AND restore-tested within 12 months."),
        specialist("endpoint", "Endpoint",
                   "EDR on 100% of endpoints incl. servers; no end-of-life OS in production."),
        specialist("vendor", "Third-party",
                   "Formal third-party/vendor security assessment process in place."),
    ]

    fan_out = ParallelAgent(name="controls", sub_agents=specialists)
    aggregator = LlmAgent(
        name="aggregator", model=MODEL,
        instruction=("Combine the specialist findings in session state into one overall "
                     "assessment: a one-line verdict then the per-domain MET/NOT MET list. "
                     "This is for a human underwriter - do not make the final decision."))
    return SequentialAgent(name="root", sub_agents=[fan_out, aggregator])


async def run_adk(submission_id: str) -> str:
    if not ADK_AVAILABLE:
        raise RuntimeError("google-adk not installed; use EVAL_MODE=plain")
    root = build_root_agent(submission_id)
    session_service = InMemorySessionService()
    await session_service.create_session(app_name="uw", user_id="svc", session_id=submission_id)
    runner = Runner(agent=root, app_name="uw", session_service=session_service)
    msg = types.Content(role="user",
                        parts=[types.Part(text=f"Assess submission {submission_id}.")])
    final = ""
    async for event in runner.run_async(user_id="svc", session_id=submission_id, new_message=msg):
        if event.is_final_response() and event.content and event.content.parts:
            final = event.content.parts[0].text
    return final
