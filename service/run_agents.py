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
