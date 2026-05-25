#!/usr/bin/env python3
"""AURA HP-Site server: serves static HTML + /api/dozent-submit proxy to AC."""
import os, json, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

AC_URL = "https://auraakademie.api-us1.com"
AC_KEY = os.environ.get("AC_API_KEY", "534a79dfddeccd8bc272c3730fb85be43c2e33193814229630e7c2c244767a67fd3bce2e")
LIST_ID_HAUPT     = 3   # Hauptkontaktliste — ALLE Leads landen hier für general marketing
LIST_ID_HP_FUNNEL = 16  # HP-App Funnel — Quiz Leads
LIST_ID_DOZENT    = 17  # Dozentenbewerbungen
TAG_ID_QUIZ_LEAD  = 51  # hp-app:quiz-lead
TAG_ID_INSTALLED  = 54  # hp-app:installed
TAG_ID_DOZENT     = 61  # DOZENT_BEWERBUNG

STATIC_DIR = "/usr/share/nginx/html"
PORT = int(os.environ.get("PORT", "8080"))

def ac_request(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(AC_URL + path, data=data,
        headers={"Api-Token": AC_KEY, "Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass  # silence

    def _serve_file(self, path):
        # Strip leading /
        rel = path.lstrip("/")
        if not rel: rel = "index.html"
        # Strip query string
        if "?" in rel: rel = rel.split("?")[0]
        # Resolve safely
        full = os.path.join(STATIC_DIR, rel)
        real = os.path.realpath(full)
        if not real.startswith(STATIC_DIR):
            self.send_response(403); self.end_headers(); return
        # If directory or missing, fall back to index.html (SPA-style)
        if os.path.isdir(real) or not os.path.exists(real):
            # try with .html
            if not rel.endswith(".html") and os.path.exists(full + ".html"):
                real = full + ".html"
            else:
                real = os.path.join(STATIC_DIR, "index.html")
        # Determine content-type
        ext = real.rsplit(".", 1)[-1].lower()
        ctype = {
            "html": "text/html; charset=utf-8",
            "xml": "application/xml; charset=utf-8",
            "txt": "text/plain; charset=utf-8",
            "css": "text/css; charset=utf-8",
            "js": "application/javascript; charset=utf-8",
            "json": "application/json; charset=utf-8",
            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "gif": "image/gif", "svg": "image/svg+xml", "ico": "image/x-icon",
            "pdf": "application/pdf",
        }.get(ext, "application/octet-stream")
        try:
            with open(real, "rb") as f: body = f.read()
        except FileNotFoundError:
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._serve_file(self.path)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode())
        except Exception:
            self._respond(400, {"ok": False, "error": "invalid_json"}); return

        if self.path == "/api/quiz-email":
            return self._handle_quiz(data)
        if self.path == "/api/dozent-submit":
            return self._handle_dozent(data)
        self.send_response(404); self.end_headers()

    def _safe_subscribe(self, contact_id, list_id):
        try:
            ac_request("POST", "/api/3/contactLists",
                {"contactList": {"list": list_id, "contact": contact_id, "status": 1}})
        except Exception: pass

    def _safe_tag(self, contact_id, tag_id):
        try:
            ac_request("POST", "/api/3/contactTags",
                {"contactTag": {"contact": contact_id, "tag": tag_id}})
        except Exception: pass

    def _handle_quiz(self, data):
        email = (data.get("email") or "").strip().lower()
        firstName = (data.get("firstName") or data.get("name") or data.get("vorname") or "").strip()
        if not email:
            self._respond(400, {"ok": False, "error": "email_required"}); return
        try:
            payload = {"contact": {"email": email}}
            if firstName: payload["contact"]["firstName"] = firstName
            sync = ac_request("POST", "/api/3/contact/sync", payload)
            cid = sync.get("contact", {}).get("id")
            if not cid:
                self._respond(500, {"ok": False, "error": "sync_failed"}); return
            self._safe_subscribe(cid, LIST_ID_HP_FUNNEL)  # 16
            self._safe_subscribe(cid, LIST_ID_HAUPT)     # 3 — general marketing
            self._safe_tag(cid, TAG_ID_QUIZ_LEAD)        # 51
            self._respond(200, {"ok": True, "contact_id": cid})
        except urllib.error.HTTPError as e:
            self._respond(500, {"ok": False, "error": f"ac_{e.code}"})
        except Exception as e:
            self._respond(500, {"ok": False, "error": str(e)[:200]})

    def _handle_dozent(self, data):
        firstName = (data.get("vorname") or "").strip()
        lastName  = (data.get("nachname") or "").strip()
        email     = (data.get("email") or "").strip().lower()
        phone     = (data.get("telefon") or "").strip()

        if not email or not firstName:
            self._respond(400, {"ok": False, "error": "vorname_and_email_required"}); return

        try:
            sync = ac_request("POST", "/api/3/contact/sync",
                {"contact": {"email": email, "firstName": firstName,
                             "lastName": lastName, "phone": phone}})
            contact_id = sync.get("contact", {}).get("id")
            if not contact_id:
                self._respond(500, {"ok": False, "error": "contact_sync_failed"}); return

            self._safe_subscribe(contact_id, LIST_ID_DOZENT)
            self._safe_tag(contact_id, TAG_ID_DOZENT)
            self._safe_subscribe(contact_id, LIST_ID_HAUPT)

            # Append all answers as a contact note (so Dennis sees full form in AC)
            try:
                summary_lines = []
                for k, v in data.items():
                    if k in ("vorname","nachname","email","telefon","form_name","submitted_at"): continue
                    if v in (None, "", []): continue
                    if isinstance(v, list): v = ", ".join(str(x) for x in v)
                    summary_lines.append(f"{k}: {v}")
                note_text = "Dozenten-Bewerbung Formular:\n\n" + "\n".join(summary_lines[:200])
                ac_request("POST", "/api/3/notes", {"note": {
                    "note": note_text[:8000],
                    "relid": contact_id,
                    "reltype": "Subscriber"
                }})
            except Exception: pass

            self._respond(200, {"ok": True, "contact_id": contact_id})
        except urllib.error.HTTPError as e:
            self._respond(500, {"ok": False, "error": f"ac_{e.code}",
                                "detail": e.read()[:200].decode(errors="ignore")})
        except Exception as e:
            self._respond(500, {"ok": False, "error": str(e)[:200]})

    def _respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)


class ThreadingServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    print(f"AURA server listening on :{PORT}  (static: {STATIC_DIR})")
    ThreadingServer(("0.0.0.0", PORT), Handler).serve_forever()
