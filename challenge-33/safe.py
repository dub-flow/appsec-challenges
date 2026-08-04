from flask import Flask, request, send_from_directory, jsonify
import requests
import ipaddress
import logging
import socket
from urllib.parse import urlparse

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

def is_disallowed(ip):
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )

@app.route('/secret')
def secret():
    try:
        remote_ip = ipaddress.ip_address(request.remote_addr)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not remote_ip.is_loopback:
        return jsonify({"error": "Forbidden"}), 403
    return send_from_directory('static', 'secret.html')

@app.route('/fetch', methods=['GET'])
def fetch_url():
    target_url = request.args.get('url')

    if not target_url:
        return jsonify({"error": "URL parameter is required"}), 400

    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return jsonify({"error": "Invalid URL"}), 400

    # Resolve the hostname exactly once, then reuse that IP for the actual
    # request. This collapses the check and the use into a single DNS answer,
    # which is what closes the DNS rebinding window.
    try:
        resolved_ip = socket.gethostbyname(parsed.hostname)
    except socket.gaierror:
        return jsonify({"error": "Could not resolve hostname"}), 400

    try:
        ip = ipaddress.ip_address(resolved_ip)
    except ValueError:
        return jsonify({"error": "Invalid resolved address"}), 400

    if is_disallowed(ip):
        return jsonify({"error": "Requests to internal addresses are not allowed."}), 400

    # Rebuild the URL with the resolved IP so requests.get does NOT do a second
    # DNS lookup. Preserve the original hostname in the Host header so
    # virtual-hosted backends still route correctly.
    port = f":{parsed.port}" if parsed.port else ""
    pinned_url = parsed._replace(netloc=f"{resolved_ip}{port}").geturl()
    original_host = parsed.netloc

    try:
        # allow_redirects=False — a redirect would re-introduce hostname
        # resolution and reopen the same TOCTOU.
        response = requests.get(
            pinned_url,
            headers={"Host": original_host},
            allow_redirects=False,
            timeout=5,
        )
        return response.text
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
