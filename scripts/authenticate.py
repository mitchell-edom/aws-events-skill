#!/usr/bin/env python3
"""
AWS Events API - OAuth 2.0 PKCE Authentication CLI
Authenticates an attendee via AWS Builder ID and securely saves the token.
Supports both automatic local callback (port 8484) and manual URL exchange.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

CLIENT_ID = "7vmom55m1qstvq8i71ph127bfq"
REDIRECT_URI = "http://localhost:8484/callback"
AUTH_ENDPOINT = "https://oauth.awsevents.com/oauth2/authorize"
TOKEN_ENDPOINT = "https://oauth.awsevents.com/oauth2/token"
SCOPES = "openid email events/access"
IDP = "AWSBuilderID"

CONFIG_DIR = os.path.expanduser("~/.gemini/config")
TOKEN_FILE = os.path.join(CONFIG_DIR, "awsevents_token.json")
PENDING_AUTH_FILE = os.path.join(CONFIG_DIR, "awsevents_pending_auth.json")
GLOBAL_MCP_CONFIG = os.path.join(CONFIG_DIR, "mcp_config.json")
WORKSPACE_MCP_CONFIG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".agents", "mcp_config.json")
)


def generate_pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode("utf-8").rstrip("=")
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


def exchange_code(code, verifier):
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code": code,
        "code_verifier": verifier,
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def save_tokens(tokens):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(TOKEN_FILE, 0o600)

    # Clean up pending auth
    if os.path.exists(PENDING_AUTH_FILE):
        try:
            os.remove(PENDING_AUTH_FILE)
        except OSError:
            pass

    # Update machine-local global mcp_config.json with Authorization header
    access_token = tokens.get("access_token")
    if access_token:
        update_mcp_config(GLOBAL_MCP_CONFIG, access_token)


def update_mcp_config(path, access_token):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r") as f:
            cfg = json.load(f)
        if "mcpServers" in cfg and "awsevents" in cfg["mcpServers"]:
            cfg["mcpServers"]["awsevents"]["headers"] = {
                "Authorization": f"Bearer {access_token}"
            }
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2)
            os.chmod(path, 0o600)
    except Exception as e:
        print(f"Notice: could not update {path}: {e}", file=sys.stderr)


class CallbackHandler(BaseHTTPRequestHandler):
    verifier = None
    expected_state = None
    auth_result = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        error = params.get("error", [None])[0]
        if error:
            error_desc = params.get("error_description", [error])[0]
            CallbackHandler.auth_result = {"error": error_desc}
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h2>Sign-in error:</h2><p>{error_desc}</p>".encode("utf-8"))
            return

        state = params.get("state", [None])[0]
        code = params.get("code", [None])[0]

        if state != CallbackHandler.expected_state:
            CallbackHandler.auth_result = {"error": "State parameter mismatch"}
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Error</h2><p>CSRF state check failed.</p>")
            return

        if not code:
            CallbackHandler.auth_result = {"error": "Missing authorization code"}
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Error</h2><p>Missing authorization code.</p>")
            return

        try:
            tokens = exchange_code(code, CallbackHandler.verifier)
            save_tokens(tokens)
            CallbackHandler.auth_result = {"success": True}
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><head><title>Success</title></head>"
                b"<body style='font-family:sans-serif;text-align:center;padding:50px;background:#f8f9fa;'>"
                b"<div style='max-width:500px;margin:auto;background:white;padding:30px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);'>"
                b"<h2 style='color:#107c41;'>Authenticated with AWS Builder ID!</h2>"
                b"<p>Your session token has been securely saved. You can close this tab and return to the assistant.</p>"
                b"</div></body></html>"
            )
        except Exception as e:
            CallbackHandler.auth_result = {"error": str(e)}
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h2>Token Exchange Failed</h2><p>{e}</p>".encode("utf-8"))


def exchange_manual(callback_url_or_code):
    if not os.path.exists(PENDING_AUTH_FILE):
        print("Error: No pending authentication session found.", file=sys.stderr)
        sys.exit(1)

    with open(PENDING_AUTH_FILE) as f:
        pending = json.load(f)

    verifier = pending.get("verifier")
    expected_state = pending.get("state")

    if not verifier:
        print("Error: Invalid pending auth state.", file=sys.stderr)
        sys.exit(1)

    # Check if a full URL was passed
    if "code=" in callback_url_or_code:
        parsed = urllib.parse.urlparse(callback_url_or_code)
        params = urllib.parse.parse_qs(parsed.query or parsed.path)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        if state and state != expected_state:
            print(f"Warning: state mismatch. Expected {expected_state}, got {state}", file=sys.stderr)
    else:
        code = callback_url_or_code.strip()

    if not code:
        print("Error: Could not extract authorization code.", file=sys.stderr)
        sys.exit(1)

    try:
        tokens = exchange_code(code, verifier)
        save_tokens(tokens)
        print("Success! Tokens exchanged and securely stored in ~/.gemini/config/awsevents_token.json")
        sys.exit(0)
    except Exception as e:
        print(f"Token exchange failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="AWS Events OAuth PKCE Authenticator")
    parser.add_argument("--callback-url", help="Exchange tokens manually from callback URL or code")
    args = parser.parse_args()

    if args.callback_url:
        exchange_manual(args.callback_url)
        return

    verifier, challenge = generate_pkce()
    state = secrets.token_hex(16)

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "identity_provider": IDP,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    auth_url = f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(PENDING_AUTH_FILE, "w") as f:
        json.dump({"verifier": verifier, "state": state, "auth_url": auth_url}, f, indent=2)
    os.chmod(PENDING_AUTH_FILE, 0o600)

    CallbackHandler.verifier = verifier
    CallbackHandler.expected_state = state

    server = HTTPServer(("127.0.0.1", 8484), CallbackHandler)
    server.timeout = 5.0  # 5 second poll interval

    print("=" * 60)
    print("AWS Events Sign-in (AWS Builder ID)")
    print("=" * 60)
    print("\nPlease open the following authorization URL in your browser to sign in:")
    print(f"\n{auth_url}\n")
    print("Listening on http://localhost:8484/callback (timeout 10m)...")
    sys.stdout.flush()

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    start_time = time.time()
    # Listen for up to 600 seconds (10 minutes)
    while time.time() - start_time < 600:
        server.handle_request()
        if CallbackHandler.auth_result is not None:
            break

    if CallbackHandler.auth_result and CallbackHandler.auth_result.get("success"):
        print("\nSuccess! Token received and stored in ~/.gemini/config/awsevents_token.json")
        print("MCP configuration files updated with authorization headers.")
        sys.exit(0)
    else:
        err = CallbackHandler.auth_result.get("error") if CallbackHandler.auth_result else "Timeout (10m elapsed)"
        print(f"\nAuthentication stopped: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
