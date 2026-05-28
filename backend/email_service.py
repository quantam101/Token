"""TokenForge — transactional email via Resend.

Sender: onboarding@resend.dev (Resend sandbox until domain is verified)
Reply-To + BCC: operator email so all outbound traffic is mirrored to inbox.

All sends are non-blocking via asyncio.to_thread().
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Optional

import resend

log = logging.getLogger("tokenforge.email")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "TokenForge <onboarding@resend.dev>")
OPERATOR_EMAIL = os.environ.get("OPERATOR_EMAIL", "dispatch@alreadyherellc.com")
# Set OPERATOR_BCC=1 in .env AFTER verifying your domain in Resend.
# Until then, Resend test-mode rejects sends with a BCC to an unverified address.
OPERATOR_BCC = os.environ.get("OPERATOR_BCC", "0") == "1"

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def _enabled() -> bool:
    return bool(RESEND_API_KEY) and not RESEND_API_KEY.startswith("placeholder")


async def send_email(
    to: str,
    subject: str,
    html: str,
    attachment: Optional[dict] = None,  # {"filename": "...", "content_bytes": b"..."}
    bcc_operator: bool = True,
) -> Optional[str]:
    """Send a transactional email. Returns email id on success, else None.
    Failure never raises — email is best-effort, never blocks app flow."""
    if not _enabled():
        log.warning("RESEND_API_KEY not configured — skipping email to %s (subject=%s)", to, subject)
        return None

    params = {
        "from": SENDER_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
        "reply_to": OPERATOR_EMAIL,
    }
    if bcc_operator and OPERATOR_BCC and OPERATOR_EMAIL and OPERATOR_EMAIL.lower() != to.lower():
        params["bcc"] = [OPERATOR_EMAIL]
    if attachment and attachment.get("content_bytes"):
        params["attachments"] = [
            {
                "filename": attachment.get("filename", "report.pdf"),
                "content": base64.b64encode(attachment["content_bytes"]).decode("ascii"),
            }
        ]
    try:
        res = await asyncio.to_thread(resend.Emails.send, params)
        log.info("resend.send ok id=%s to=%s subject=%s", res.get("id"), to, subject)
        return res.get("id")
    except Exception as e:  # noqa: BLE001 - best effort
        log.exception("resend.send failed to=%s: %s", to, e)
        return None


# ----------------------------------------------------------------------
# Branded HTML templates (table-based, inline CSS, email-safe).
# ----------------------------------------------------------------------
BRAND_HEAD = """\
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#0A0A0A;color:#FAFAFA;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <tr><td align="center" style="padding:32px 16px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560" style="max-width:560px;background:#121212;border:1px solid #27272A;border-radius:6px;">
      <tr><td style="padding:24px 28px;border-bottom:1px solid #27272A;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
          <td style="background:#FF4500;width:28px;height:28px;text-align:center;color:#000;font-weight:800;font-size:13px;line-height:28px;">TF</td>
          <td style="padding-left:10px;color:#FAFAFA;font-weight:800;letter-spacing:-0.4px;font-size:18px;">TokenForge</td>
        </tr></table>
      </td></tr>
"""

BRAND_FOOT = """\
      <tr><td style="padding:16px 28px;border-top:1px solid #27272A;color:#71717A;font-size:11px;line-height:1.6;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;">
        TokenForge — distill or perish.<br>
        You're receiving this because you have an account at tokenforge.io.<br>
        Reply directly to this email to reach our team.
      </td></tr>
    </table>
  </td></tr>
</table>
"""

def _block(inner: str) -> str:
    return BRAND_HEAD + f'<tr><td style="padding:28px;">{inner}</td></tr>' + BRAND_FOOT


def render_welcome(user_name: str, api_key: str, dashboard_url: str) -> str:
    return _block(f"""\
<h1 style="margin:0 0 12px;font-size:24px;letter-spacing:-0.6px;color:#FAFAFA;">Welcome to the forge, {user_name}.</h1>
<p style="margin:0 0 18px;color:#A1A1AA;font-size:14px;line-height:1.6;">
Your account is live. Below is your default API key — use it to start saving tokens immediately.
</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#1A1A1A;border:1px solid #27272A;border-radius:4px;margin:8px 0 20px;">
  <tr><td style="padding:14px 16px;color:#FF4500;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:13px;word-break:break-all;">{api_key}</td></tr>
</table>
<p style="margin:0 0 8px;color:#FAFAFA;font-size:14px;font-weight:600;">Quickstart — drop this into a terminal:</p>
<pre style="margin:0 0 20px;padding:14px 16px;background:#1A1A1A;border:1px solid #27272A;border-radius:4px;color:#FAFAFA;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;">curl -X POST https://api.tokenforge.io/api/proxy/chat \\
  -H "X-TF-Key: {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"prompt":"Summarize this in 2 bullets..."}}'</pre>
<p style="margin:0 0 22px;color:#A1A1AA;font-size:14px;line-height:1.6;">
You get <b style="color:#00E676;">50,000 free tokens / month</b>. The dashboard shows tokens saved, $ saved, and a downloadable ROI report.
</p>
<a href="{dashboard_url}" style="display:inline-block;background:#FF4500;color:#000;font-weight:600;padding:12px 22px;border-radius:4px;text-decoration:none;font-size:14px;">Open Dashboard →</a>
""")


def render_quota_alert(
    user_name: str, percent: float, used: int, quota: int, exceeded: bool, billing_url: str
) -> str:
    color = "#F44336" if exceeded else "#FFB300"
    badge = "QUOTA EXCEEDED" if exceeded else "QUOTA WARNING"
    headline = (
        "You've hit 100% of your monthly token quota."
        if exceeded
        else f"You're at {percent:.0f}% of your monthly token quota."
    )
    body_sub = (
        "Proxy calls will return HTTP 429 until next month or an upgrade. Existing logs and reports remain available."
        if exceeded
        else "Heads up — we'll keep you posted as you cross 100%."
    )
    return _block(f"""\
<div style="display:inline-block;padding:4px 10px;border:1px solid {color};color:{color};font-size:11px;letter-spacing:0.16em;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;border-radius:2px;margin-bottom:12px;">{badge}</div>
<h1 style="margin:0 0 8px;font-size:22px;letter-spacing:-0.5px;color:#FAFAFA;">Hey {user_name},</h1>
<p style="margin:0 0 14px;color:#FAFAFA;font-size:15px;line-height:1.55;">{headline}</p>
<p style="margin:0 0 18px;color:#A1A1AA;font-size:13px;line-height:1.6;">{body_sub}</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#1A1A1A;border:1px solid #27272A;border-radius:4px;margin:8px 0 22px;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:13px;">
  <tr><td style="padding:14px 16px;color:#A1A1AA;">Used this period</td><td style="padding:14px 16px;text-align:right;color:{color};">{used:,} tk</td></tr>
  <tr><td style="padding:14px 16px;color:#A1A1AA;border-top:1px solid #27272A;">Monthly quota</td><td style="padding:14px 16px;text-align:right;color:#FAFAFA;border-top:1px solid #27272A;">{quota:,} tk</td></tr>
  <tr><td style="padding:14px 16px;color:#A1A1AA;border-top:1px solid #27272A;">Utilization</td><td style="padding:14px 16px;text-align:right;color:{color};border-top:1px solid #27272A;">{percent:.0f}%</td></tr>
</table>
<a href="{billing_url}" style="display:inline-block;background:#FF4500;color:#000;font-weight:600;padding:12px 22px;border-radius:4px;text-decoration:none;font-size:14px;">{("Upgrade plan →" if exceeded else "Manage plan →")}</a>
""")


def render_payment_confirmation(user_name: str, plan_name: str, amount: float, cycle: str, dashboard_url: str) -> str:
    return _block(f"""\
<div style="display:inline-block;padding:4px 10px;border:1px solid #00E676;color:#00E676;font-size:11px;letter-spacing:0.16em;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;border-radius:2px;margin-bottom:12px;">PAYMENT RECEIVED</div>
<h1 style="margin:0 0 8px;font-size:22px;letter-spacing:-0.5px;color:#FAFAFA;">Thanks, {user_name}.</h1>
<p style="margin:0 0 16px;color:#A1A1AA;font-size:14px;line-height:1.6;">
Your <b style="color:#FAFAFA;">{plan_name}</b> plan is now active. Your new quota will refresh at the start of every billing period.
</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#1A1A1A;border:1px solid #27272A;border-radius:4px;margin:8px 0 22px;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:13px;">
  <tr><td style="padding:12px 16px;color:#A1A1AA;">Plan</td><td style="padding:12px 16px;text-align:right;color:#FAFAFA;">{plan_name}</td></tr>
  <tr><td style="padding:12px 16px;color:#A1A1AA;border-top:1px solid #27272A;">Billing cycle</td><td style="padding:12px 16px;text-align:right;color:#FAFAFA;border-top:1px solid #27272A;">{cycle}</td></tr>
  <tr><td style="padding:12px 16px;color:#A1A1AA;border-top:1px solid #27272A;">Amount</td><td style="padding:12px 16px;text-align:right;color:#00E676;border-top:1px solid #27272A;">${amount:.2f}</td></tr>
</table>
<a href="{dashboard_url}" style="display:inline-block;background:#FF4500;color:#000;font-weight:600;padding:12px 22px;border-radius:4px;text-decoration:none;font-size:14px;">Open dashboard →</a>
""")


def render_roi_report_email(user_name: str, tokens_saved: int, cost_saved: float, dashboard_url: str) -> str:
    return _block(f"""\
<h1 style="margin:0 0 8px;font-size:22px;letter-spacing:-0.5px;color:#FAFAFA;">Your monthly savings report, {user_name}.</h1>
<p style="margin:0 0 18px;color:#A1A1AA;font-size:14px;line-height:1.6;">
This month TokenForge distilled your prompts and avoided sending unnecessary tokens upstream. Here's the receipt.
</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 22px;">
  <tr>
    <td style="width:50%;padding:0 6px 0 0;">
      <div style="background:#1A1A1A;border:1px solid #27272A;border-radius:4px;padding:18px;">
        <div style="color:#71717A;font-size:11px;letter-spacing:0.14em;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;">TOKENS SAVED</div>
        <div style="color:#00E676;font-size:30px;font-weight:800;margin-top:4px;letter-spacing:-0.6px;">{tokens_saved:,}</div>
      </div>
    </td>
    <td style="width:50%;padding:0 0 0 6px;">
      <div style="background:#1A1A1A;border:1px solid #27272A;border-radius:4px;padding:18px;">
        <div style="color:#71717A;font-size:11px;letter-spacing:0.14em;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;">$ SAVED</div>
        <div style="color:#FF4500;font-size:30px;font-weight:800;margin-top:4px;letter-spacing:-0.6px;">${cost_saved:.4f}</div>
      </div>
    </td>
  </tr>
</table>
<p style="margin:0 0 22px;color:#A1A1AA;font-size:13px;line-height:1.6;">
The full PDF is attached — share it with your CFO or your team. You can regenerate it anytime from the dashboard.
</p>
<a href="{dashboard_url}" style="display:inline-block;background:#FF4500;color:#000;font-weight:600;padding:12px 22px;border-radius:4px;text-decoration:none;font-size:14px;">Open dashboard →</a>
""")
