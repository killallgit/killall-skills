#!/usr/bin/env python3
"""Send mail via Proton Bridge. Usage: cat message | proton-send.py recipient@example.com"""
import smtplib, ssl, os, sys

env = {}
with open(os.path.expanduser('~/.openclaw/.env')) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k] = v

pw = env['PROTON_BRIDGE_PASSWORD']
msg = sys.stdin.buffer.read()
recipients = sys.argv[1:] if len(sys.argv) > 1 else ['lowt0ner@pm.me']

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with smtplib.SMTP_SSL('127.0.0.1', 1025, context=ctx, timeout=30) as smtp:
    smtp.login('lowt0ner@pm.me', pw)
    smtp.sendmail('lowt0ner@pm.me', recipients, msg)
