# How to Hack

The app in this challenge is vulnerable to a Server-Side Request Forgery via DNS Rebinding. The `/fetch` endpoint takes a user-supplied URL and tries to prevent it from pointing at internal addresses by checking whether the hostname resolves to a loopback IP. Only if that check passes does it actually fetch the URL with `requests.get`.

The bug is a classic Time-Of-Check / Time-Of-Use: the hostname is resolved twice. Once inside `is_localhost()` for the safety check, and a second time inside `requests.get()` when the actual HTTP request happens. A malicious DNS server that returns a different answer on the second lookup can bypass the check entirely.

The setup:

- `/secret` is gated by `is_localhost(request.remote_addr)`, so it is only reachable from `127.0.0.1`.
- Our goal is to make the app itself send a request to `127.0.0.1:5000/secret`, so the response comes from a loopback peer.

The exploit (see `./exploit.sh`) uses `rbndr.us`, a free DNS rebinding service. The host `08080808.7f000001.rbndr.us` alternates between `8.8.8.8` and `127.0.0.1` on each query. We hit the endpoint repeatedly:

```
curl 'http://localhost:5000/fetch?url=http://08080808.7f000001.rbndr.us:5000/secret'
```

Roughly half the attempts return `400 Requests to localhost are not allowed` (the rebind happened on the precheck) and the other half return the secret HTML (the rebind happened on the actual fetch). On a flip in our favor, the request loops back into the same Flask app, hits `/secret` from `127.0.0.1`, and the secret is returned.

In the real world, this same trick is used to reach cloud metadata endpoints (`http://169.254.169.254/...`), internal admin panels, and other services that the SSRF filter thought it had blocked.

# How to Fix

The root cause is that the hostname is resolved twice and the two answers can disagree. The fix is to resolve it exactly once, validate that single answer, and then make the HTTP request to the resolved IP directly — so there is no second DNS lookup that an attacker can influence (see `./safe.py`).

Concretely:

1. Parse the URL and extract the hostname.
2. Resolve the hostname to an IP a single time.
3. Reject loopback (and ideally private, link-local, multicast, etc.) addresses.
4. Rebuild the URL with the resolved IP in place of the hostname, and pass the original hostname in the `Host` header so virtual-hosted backends still work.
5. Disable redirect following, because each redirect would otherwise re-introduce hostname resolution and the same TOCTOU.

This pattern is sometimes called "pinning" the DNS resolution. It collapses the check and the use into a single decision over a single IP, which is what removes the rebinding window.

As defense in depth, I'd also restrict the allowed URL schemes to `http`/`https` and block obvious internal ranges explicitly, so a typo or a future refactor in the resolver logic doesn't silently re-open the SSRF.
