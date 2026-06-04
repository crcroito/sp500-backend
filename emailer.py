import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict

def build_html_email(signals: List[Dict], date: str) -> str:
    rows = ""
    for s in signals[:15]:  # max 15 în email
        sig = s["signals"]
        icons = ""
        if sig.get("earnings_surprise"):  icons += "📈"
        if sig.get("analyst_revision"):   icons += "🎯"
        if sig.get("volume_anomaly"):     icons += "🔊"
        if sig.get("relative_strength"): icons += "💪"
        if sig.get("inst_accumulation"): icons += "🏦"

        score_color = "#00ff94" if s["score"] >= 4 else "#ffcc00"
        chg_color   = "#00ff94" if s["change_1d"] >= 0 else "#ff4060"

        notes_html = ""
        for k, v in s["notes"].items():
            if v:
                notes_html += f"<div style='font-size:11px;color:#5a7385;margin-top:2px'>• {v}</div>"

        rows += f"""
        <tr style='border-bottom:1px solid #1a2535'>
          <td style='padding:12px 10px'>
            <div style='font-weight:700;color:#00d4ff;font-size:15px'>{s['ticker']}</div>
            <div style='font-size:11px;color:#5a7385'>{s['name']}</div>
          </td>
          <td style='padding:12px 10px;font-size:11px;color:#5a7385'>{s['sector']}</td>
          <td style='padding:12px 10px;text-align:center'>
            <span style='font-size:22px;font-weight:900;color:{score_color}'>{s['score']}/5</span>
          </td>
          <td style='padding:12px 10px;font-size:16px'>{icons}</td>
          <td style='padding:12px 10px;font-weight:700;color:{chg_color}'>
            {'+' if s['change_1d'] >= 0 else ''}{s['change_1d']}%
          </td>
          <td style='padding:12px 10px'>
            <div style='font-size:12px'>${s['price']}</div>
            {notes_html}
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style='background:#050709;color:#dce8f0;font-family:IBM Plex Mono,monospace;margin:0;padding:20px'>
  <div style='max-width:800px;margin:0 auto'>

    <div style='padding:20px 0;border-bottom:1px solid #1a2535;margin-bottom:24px'>
      <div style='font-size:22px;font-weight:900'>
        S&P<span style='color:#00d4ff'>500</span>
        <span style='font-size:10px;background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.2);color:#00d4ff;padding:2px 8px;border-radius:2px;letter-spacing:2px;margin-left:8px'>INTELLIGENCE</span>
      </div>
      <div style='font-size:12px;color:#5a7385;margin-top:6px'>🚨 Early Warning Report · {date}</div>
    </div>

    <div style='background:rgba(0,255,148,0.05);border:1px solid rgba(0,255,148,0.2);border-radius:6px;padding:14px;margin-bottom:20px;font-size:12px;line-height:1.7'>
      <strong style='color:#00ff94'>📌 {len(signals)} companii</strong> din S&P 500 aprind <strong>4-5 semne simultane</strong> azi.<br>
      Acestea sunt candidatele cele mai puternice înainte ca piața să le descopere.
    </div>

    <table style='width:100%;border-collapse:collapse'>
      <thead>
        <tr style='border-bottom:2px solid #1a2535'>
          <th style='padding:8px 10px;text-align:left;font-size:9px;color:#5a7385;text-transform:uppercase;letter-spacing:1px'>Ticker</th>
          <th style='padding:8px 10px;text-align:left;font-size:9px;color:#5a7385;text-transform:uppercase;letter-spacing:1px'>Sector</th>
          <th style='padding:8px 10px;text-align:center;font-size:9px;color:#5a7385;text-transform:uppercase;letter-spacing:1px'>Scor</th>
          <th style='padding:8px 10px;font-size:9px;color:#5a7385;text-transform:uppercase;letter-spacing:1px'>Semne</th>
          <th style='padding:8px 10px;font-size:9px;color:#5a7385;text-transform:uppercase;letter-spacing:1px'>1D</th>
          <th style='padding:8px 10px;font-size:9px;color:#5a7385;text-transform:uppercase;letter-spacing:1px'>Detalii</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>

    <div style='margin-top:24px;padding:14px;background:#0b0f14;border:1px solid #1a2535;border-radius:6px;font-size:10px;color:#3d5468;line-height:1.8'>
      <strong>Legendă semne:</strong> 📈 Earnings Surprise &nbsp;|&nbsp; 🎯 Analyst Revision &nbsp;|&nbsp;
      🔊 Volume Anomaly &nbsp;|&nbsp; 💪 Relative Strength &nbsp;|&nbsp; 🏦 Institutional Accumulation<br>
      <strong style='color:#ff4060'>⚠️ Disclaimer:</strong> Aceasta nu este recomandare de investiție. Fă research propriu înainte de orice decizie.
    </div>

    <div style='margin-top:16px;text-align:center;font-size:10px;color:#3d5468'>
      S&P500 Intelligence · Generat automat · {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC
    </div>
  </div>
</body>
</html>"""


def send_alert_email(signals: List[Dict], to_email: str):
    """Trimite email cu alertele zilnice."""
    if not signals:
        return False

    smtp_host  = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port  = int(os.getenv("SMTP_PORT", "587"))
    smtp_user  = os.getenv("SMTP_USER", "")
    smtp_pass  = os.getenv("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        print("⚠️ SMTP credentials not configured")
        return False

    date_str = datetime.now().strftime("%d %B %Y")
    html_body = build_html_email(signals, date_str)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 S&P500 Early Warning — {len(signals)} semnale · {date_str}"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False
