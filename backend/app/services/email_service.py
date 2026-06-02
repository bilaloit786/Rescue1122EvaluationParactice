import resend
from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY or ""


def _result_html(staff_name: str, designation: str, district: str, topic: str,
                 score_pct: float, correct: int, total: int, passed: bool, feedback: str) -> str:
    color = "#3B6D11" if passed else "#993C1D"
    bg = "#EAF3DE" if passed else "#FAECE7"
    status = "PASSED" if passed else "FAILED"
    return f"""
<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
<div style="background:#185FA5;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:20px;">Rescue 1122 — Staff Evaluation Report</h1>
  <p style="color:#B5D4F4;margin:6px 0 0;">Punjab Emergency Service</p>
</div>
<div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
  <table width="100%" style="margin-bottom:20px;"><tr>
    <td><strong>Name:</strong> {staff_name}<br><strong>Designation:</strong> {designation}<br><strong>District:</strong> {district}</td>
    <td style="text-align:right;vertical-align:top;"><strong>Topic:</strong> {topic}</td>
  </tr></table>
  <div style="text-align:center;padding:20px;background:{bg};border-radius:8px;margin-bottom:20px;">
    <div style="font-size:48px;font-weight:bold;color:{color};">{score_pct:.0f}%</div>
    <div style="font-size:18px;color:{color};font-weight:bold;">{status}</div>
    <div style="color:#666;margin-top:4px;">{correct} correct out of {total} questions</div>
  </div>
  <h3 style="color:#185FA5;border-bottom:1px solid #ddd;padding-bottom:8px;">AI Evaluation & Recommendations</h3>
  <div style="line-height:1.7;color:#444;">{feedback.replace(chr(10), '<br>')}</div>
  <div style="margin-top:24px;padding:16px;background:#f5f5f5;border-radius:6px;font-size:13px;color:#666;text-align:center;">
    This is an automated report from the Rescue 1122 Staff Evaluation System.<br>
    For queries contact your district training officer.
  </div>
</div></body></html>"""


async def send_result_email(
    to_email: str,
    staff_name: str,
    designation: str,
    district: str,
    topic: str,
    score_pct: float,
    correct: int,
    total: int,
    passed: bool,
    feedback: str
) -> bool:
    if not settings.RESEND_API_KEY:
        return False
    try:
        status_word = "Passed" if passed else "Failed"
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": f"Rescue 1122 Evaluation Result — {topic} ({status_word} {score_pct:.0f}%)",
            "html": _result_html(
                staff_name, designation, district, topic,
                score_pct, correct, total, passed, feedback
            ),
        })
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False
