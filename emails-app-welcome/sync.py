#!/usr/bin/env python3
"""
AURA App Welcome Sequenz — Email Sync to ActiveCampaign
Automation 72 (Trigger Tag hp-app:installed)

Liest mail-N.md (Markdown + Frontmatter), rendert in die AURA Email-Vorlage,
pusht via API zu AC Messages.
"""
import os, sys, re, json, glob, urllib.request, urllib.error

AC_URL = "https://auraakademie.api-us1.com"
AC_KEY = "534a79dfddeccd8bc272c3730fb85be43c2e33193814229630e7c2c244767a67fd3bce2e"

LIVE_MSG_MAP = {1: 208, 2: 209, 3: 210}
LIVE_CMP_MAP = {1: 234, 2: 236, 3: 238}

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "state.json")

SENDER_NAME  = "Heilpraktikerin Jessie"
SENDER_EMAIL = "support@auraakademie.de"

# Rundes Jessie-Portrait (96x96). Wird ausgetauscht sobald finales Foto da ist.
JESSIE_IMG = "https://heilpraktiker-pruefungsfragen.io/assets/jessie-avatar.png?v=5"

# ===== TEMPLATE =====
def render_email(subject, preheader, body_paragraphs_html, signoff, cta_text=None, cta_url=None):
    cta_block = ""
    if cta_text and cta_url:
        cta_block = f'''
          <tr>
            <td align="center" style="padding:24px 40px;">
              <a href="{cta_url}" style="display:inline-block;background-color:#BF9056;color:#FDFCF9;font-family:Arial,sans-serif;font-size:15px;font-weight:bold;text-decoration:none;padding:14px 32px;border-radius:3px;letter-spacing:0.05em;">{cta_text}</a>
            </td>
          </tr>'''
    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#F5F4F0;font-family:Arial,Helvetica,sans-serif;">
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;color:#F5F4F0;">{preheader}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F5F4F0;">
  <tr><td align="center" style="padding:32px 16px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#FDFCF9;border-radius:4px;overflow:hidden;">
      <tr><td style="background-color:#BF9056;height:4px;font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td align="center" style="padding:40px 40px 24px 40px;background-color:#FDFCF9;">
        <img src="{JESSIE_IMG}" alt="Jessie Oberbanscheidt" width="96" height="96" style="display:block;width:96px;height:96px;border-radius:50%;object-fit:cover;border:1.5px solid rgba(191,144,86,0.6);margin:0 auto 16px auto;"/>
        <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;color:#BF9056;letter-spacing:0.15em;text-transform:uppercase;font-weight:bold;">Jessie Oberbanscheidt</p>
        <p style="margin:4px 0 0 0;font-family:Arial,sans-serif;font-size:11px;color:#A6A5A4;letter-spacing:0.1em;text-transform:uppercase;">Aura Heilpraktiker Akademie</p>
      </td></tr>
      <tr><td style="padding:0 40px;"><div style="height:1px;background-color:#E8E6E0;"></div></td></tr>
      <tr><td style="padding:32px 40px 8px 40px;">
{body_paragraphs_html}
      </td></tr>{cta_block}
      <tr><td style="padding:8px 40px 40px 40px;">
        <p style="margin:0;font-family:Arial,sans-serif;font-size:16px;line-height:1.7;color:#0D0D0D;">{signoff}</p>
      </td></tr>
      <tr><td style="padding:0 40px;"><div style="height:1px;background-color:#E8E6E0;"></div></td></tr>
      <tr><td style="padding:24px 40px 32px 40px;" align="center">
        <p style="margin:0 0 8px 0;font-family:Arial,sans-serif;font-size:11px;color:#A6A5A4;line-height:1.6;text-align:center;">Wir helfen Heilpraktikerinnen, ihre Pr&uuml;fung zu bestehen.<br/>Aura Heilpraktiker Akademie &middot; Aura Global Digital LLC</p>
        <p style="margin:0;font-family:Arial,sans-serif;font-size:11px;color:#A6A5A4;line-height:1.6;text-align:center;">Du erh&auml;ltst diese Mail weil du dich in unsere Liste eingetragen hast.<br/><a href="%UNSUBSCRIBELINK%" style="color:#A6A5A4;text-decoration:underline;">Abmelden</a></p>
      </td></tr>
      <tr><td style="background-color:#BF9056;height:2px;font-size:0;line-height:0;">&nbsp;</td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>'''

# ===== Markdown → Paragraph-HTML =====
def md_paragraphs_to_html(md_body: str) -> str:
    """Body Paragraphs. Erste Zeile "Liebe %FIRSTNAME%," wird automatisch eingebaut wenn fehlt."""
    paragraphs = re.split(r"\n\s*\n", md_body.strip())
    out = []
    for p in paragraphs:
        p = p.strip()
        if not p: continue
        p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" style="color:#0D0D0D;text-decoration:underline;">\1</a>', p)
        p = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", p)
        p = p.replace("\n", "<br>\n")
        out.append(f'<p style="margin:0 0 20px 0;font-family:Arial,sans-serif;font-size:16px;line-height:1.7;color:#0D0D0D;">{p}</p>')
    return "\n".join(out)

def html_to_text(body_html, signoff):
    t = re.sub(r"<br\s*/?>", "\n", body_html + "\n" + signoff)
    t = re.sub(r"</p>", "\n\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return t.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").strip()

# ===== Frontmatter parse =====
def parse_md(path: str) -> dict:
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n(.*)", txt, re.DOTALL)
    if not m: raise ValueError(f"No frontmatter in {path}")
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip().strip('"').strip("'")
            fm[k.strip()] = v
    fm["body"] = m.group(2).strip()
    return fm

# ===== AC helper =====
def ac(method: str, path: str, payload: dict = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(AC_URL + path, data=data,
        headers={"Api-Token": AC_KEY, "Content-Type": "application/json"}, method=method)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"AC {method} {path} -> {e.code}: {e.read()[:300].decode(errors='ignore')}")

def main():
    dry = "--dry" in sys.argv
    write_html = "--html" in sys.argv

    for f in sorted(glob.glob(os.path.join(HERE, "mail-*.md"))):
        fm = parse_md(f)
        mail_n = int(fm["mail"])
        print(f"\n— Mail {mail_n}: {fm['subject']}")

        body_html = md_paragraphs_to_html(fm["body"])
        signoff = fm.get("signoff", "Jessie")
        cta_text = fm.get("cta_text")
        cta_url  = fm.get("cta_url")

        html = render_email(fm["subject"], fm.get("preheader",""), body_html, signoff, cta_text, cta_url)
        text = html_to_text(body_html, signoff)

        if write_html:
            out = os.path.join(HERE, f"preview-{mail_n}.html")
            open(out, "w").write(html)
            print(f"  ✓ wrote {out}")

        msg_id = LIVE_MSG_MAP.get(mail_n)
        if not msg_id:
            print(f"  [skip] no message_id mapped")
            continue
        if dry:
            print(f"  [dry] would update message {msg_id}")
            continue

        msg_payload = {"message": {
            "name": f"App Welcome Mail {mail_n}",
            "subject": fm["subject"],
            "preheader_text": fm.get("preheader", ""),
            "fromname": SENDER_NAME, "fromemail": SENDER_EMAIL, "reply2": SENDER_EMAIL,
            "html": html, "text": text, "format": "mime",
        }}
        ac("PUT", f"/api/3/messages/{msg_id}", msg_payload)
        print(f"  ✓ updated message {msg_id}")

        cid = LIVE_CMP_MAP.get(mail_n)
        if cid:
            try:
                ac("PUT", f"/api/3/campaigns/{cid}", {"campaign":{"name":f"App Welcome Mail {mail_n}", "subject":fm["subject"]}})
            except: pass

    print("\nDone.")

if __name__ == "__main__":
    main()
