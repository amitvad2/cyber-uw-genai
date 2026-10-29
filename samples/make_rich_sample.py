"""Generate a ~100-page cyber submission where controls are SCATTERED far apart and use
applicant vocabulary that differs from the rulebook. This is what makes a single top-k
retrieval insufficient, so the agent's reason->act->observe loop genuinely fires.

Design (why the loop must loop):
 - MFA remote access stated on p.6, but the admin-account exclusion is buried on p.78
   -> one "MFA" query won't pull both; the specialist must re-query for admin accounts.
 - Backups described as "WORM retention lock" on p.41 (never says "immutable")
   -> vocabulary mismatch; the specialist must re-query with related terms.
 - EOL hosts mentioned on p.90; restore-test gap on p.44.
"""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

PAGES = 100
# page -> real control sentences to plant (everything else is filler)
plants = {
    6:  ["3.1 Remote access: MFA is enforced for all VPN and remote desktop sessions."],
    41: ["7.4 Backup storage uses WORM retention lock with a 35-day retention window.",
         "    Backups are replicated nightly to a second region."],
    44: ["7.9 The most recent backup restore test on record was completed 18 months ago."],
    61: ["9.2 EDR (CrowdStrike Falcon) is deployed across corporate laptops and desktops."],
    78: ["12.6 MFA is NOT currently enforced for corporate email or for privileged",
         "     administrator and domain-admin accounts; rollout is planned but not scheduled."],
    90: ["14.3 Two Windows Server 2012 hosts remain in production on the warehouse network."],
    96: ["15.1 There is no formal third-party or vendor security assessment process."],
}
filler = ("This section documents operational context, organisational background, and "
          "general IT estate information provided by the applicant for underwriting review. ")

c = canvas.Canvas("rich_submission.pdf", pagesize=A4)
width, height = A4
for p in range(1, PAGES + 1):
    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, f"Cyber Insurance Submission - Northwind Logistics Ltd    (page {p}/{PAGES})")
    y -= 1.0 * cm
    c.setFont("Helvetica", 10)
    for line in plants.get(p, []):
        c.drawString(2 * cm, y, line); y -= 0.6 * cm
    # filler to make each page substantial (and push controls apart in the index)
    import textwrap
    for _ in range(6):
        for seg in textwrap.wrap(filler * 2, 95):
            c.drawString(2 * cm, y, seg); y -= 0.5 * cm
            if y < 2 * cm:
                break
        if y < 2 * cm:
            break
    c.showPage()
c.save()
print(f"Wrote rich_submission.pdf ({PAGES} pages; controls on pages {sorted(plants)})")
