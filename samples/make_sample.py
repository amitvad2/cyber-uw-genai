"""Generate a realistic cyber-insurance questionnaire PDF with deliberate control gaps."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

lines = [
    "CYBER INSURANCE SUBMISSION - SECURITY QUESTIONNAIRE",
    "Applicant: Northwind Logistics Ltd", "",
    "1. Multi-Factor Authentication (MFA)",
    "   MFA is enabled for remote VPN access only.",
    "   MFA is NOT enforced for email or privileged admin accounts.", "",
    "2. Backups",
    "   Backups run weekly to cloud storage.",
    "   Backups are NOT immutable and have not been restore-tested in 18 months.", "",
    "3. Endpoint Detection and Response (EDR)",
    "   EDR (CrowdStrike) is deployed on 92% of endpoints.",
    "   Servers in the warehouse network are excluded.", "",
    "4. Patch Management",
    "   Critical patches applied within 30 days.",
    "   Two legacy Windows Server 2012 hosts remain in production.", "",
    "5. Incident Response",
    "   A written IR plan exists but was last tested over 24 months ago.", "",
    "6. Third-Party / Supply Chain",
    "   No formal vendor security assessment process is in place.",
]
c = canvas.Canvas("sample_submission.pdf", pagesize=A4)
_, height = A4
y = height - 2 * cm
c.setFont("Helvetica", 11)
for line in lines:
    c.drawString(2 * cm, y, line); y -= 0.7 * cm
c.save()
print("Wrote sample_submission.pdf")
