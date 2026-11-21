"""P4.7.1 — SSRF-safe image retrieval (SEC-R2-02).

Before this module, ``app.cv`` validated image URLs by returning *warnings* and
then fetched them anyway, following redirects and with no size cap. This module
is now the ONLY place in ``app.cv`` allowed to make an outbound image request.

Policy, all fail-closed:

1. **Static validation** (:func:`assert_image_url_allowed`, no network): only
   ``https``; no credentials in the URL; default port only; no IP literals in
   private / loopback / link-local / metadata / reserved space; no ambiguous
   numeric host encodings; no internal-looking hostnames.
2. **Deny by default**: a syntactically valid public URL is still NOT fetched
   unless its host is on the operator allow-list ``CV_IMAGE_FETCH_ALLOWED_HOSTS``.
   The default is an empty list, i.e. no remote image fetch at all. Uploaded
   bytes (``image_data_b64``) are the preferred image source.
3. **Pinned resolution**: the host is resolved once, every resolved address must
   be globally routable, and the connection is made to that exact address (TLS
   SNI and certificate verification still use the hostname). The address that
   was validated is the address that is connected to, so DNS rebinding cannot
   swap in an internal target between check and use.
4. **No redirects**: a 3xx response is a rejection, never followed.
5. **Bounded**: hard connect/read timeouts and a streamed size cap.

Nothing here logs URLs with credentials, response bodies, or image bytes.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_CONNECT_TIMEOUT = 3.0
DEFAULT_READ_TIMEOUT = 5.0

_ALLOWED_SCHEME = "https"
_ALLOWED_PORTS = {None, 443}

_BLOCKED_HOSTNAMES = frozenset({
    "localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback",
    "metadata", "metadata.google.internal", "instance-data",
})
_BLOCKED_SUFFIXES = (
    ".local", ".localhost", ".internal", ".intranet", ".lan", ".home",
    ".corp", ".localdomain", ".svc", ".cluster.local", ".onion",
)

# Explicitly prohibited ranges in addition to ``ipaddress``'s own
# private/loopback/link-local/reserved/multicast classification.
_EXTRA_BLOCKED_NETS = tuple(ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "100.64.0.0/10", "169.254.0.0/16", "192.0.0.0/24",
    "192.0.2.0/24", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
    "224.0.0.0/4", "240.0.0.0/4", "64:ff9b::/96", "2001:db8::/32",
    "fc00::/7", "fe80::/10", "ff00::/8",
))


class UnsafeImageURLError(ValueError):
    """The image URL is prohibited and MUST NOT be fetched."""


class ImageFetchNotPermittedError(UnsafeImageURLError):
    """The URL is well-formed and public but its host is not on the allow-list."""


class ImageFetchError(RuntimeError):
    """An allowed fetch failed (network error, redirect, oversize, bad status)."""


@dataclass(frozen=True)
class ValidatedImageURL:
    url: str
    host: str
    port: int
    path_and_query: str


def _is_prohibited_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # Unwrap IPv4-mapped / 6to4-style embeddings so ::ffff:127.0.0.1 is judged
    # as 127.0.0.1.
    # as 127.0.0.1, and a 6to4 / Teredo address is judged by its embedded IPv4.
    for attr in ("ipv4_mapped", "sixtofour"):
        embedded = getattr(ip, attr, None)
        if embedded is not None:
            return _is_prohibited_ip(embedded)
    teredo = getattr(ip, "teredo", None)
    if teredo is not None:
        return True
    if (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        or ip.is_reserved or ip.is_unspecified
    ):
        return True
    if getattr(ip, "is_site_local", False):
        return True
    if any(ip in net for net in _EXTRA_BLOCKED_NETS if net.version == ip.version):
        return True
    return not ip.is_global


def _numeric_label(label: str) -> bool:
    low = label.lower()
    if low.startswith("0x"):
        return len(low) > 2 and all(c in "0123456789abcdef" for c in low[2:])
    return low.isdigit()


def _looks_like_numeric_host(host: str) -> bool:
    """True for hosts a resolver may read as an IP although ``ipaddress`` does
    not (decimal ``2130706433``, hex ``0x7f000001``, octal ``0177.0.0.1``,
    short forms ``127.1``). These are rejected outright as ambiguous."""
    labels = host.split(".")
    return all(lbl != "" and _numeric_label(lbl) for lbl in labels)


def allowed_fetch_hosts() -> frozenset[str]:
    raw = os.getenv("CV_IMAGE_FETCH_ALLOWED_HOSTS", "")
    return frozenset(h.strip().lower().rstrip(".") for h in raw.split(",") if h.strip())


def assert_image_url_allowed(url: str) -> ValidatedImageURL:
    """Static, network-free validation. Raises :class:`UnsafeImageURLError`.

    Passing this check means the URL is not *prohibited*; it does not mean the
    URL may be fetched (see :func:`fetch_image_bytes` and the allow-list).
    """
    if not isinstance(url, str) or not url.strip():
        raise UnsafeImageURLError("Image URL is empty.")
    if len(url) > 2048:
        raise UnsafeImageURLError("Image URL is too long.")
    if any(ch in url for ch in ("\r", "\n", "\t", " ", "\x00")):
        raise UnsafeImageURLError("Image URL contains whitespace or control characters.")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise UnsafeImageURLError("Image URL is malformed.") from exc

    if parts.scheme.lower() != _ALLOWED_SCHEME:
        raise UnsafeImageURLError("Only https image URLs are accepted.")
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        raise UnsafeImageURLError("Image URL must not contain credentials.")
    if port not in _ALLOWED_PORTS:
        raise UnsafeImageURLError("Image URL must use the default https port.")

    host = (parts.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise UnsafeImageURLError("Image URL has no host.")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if _is_prohibited_ip(literal):
            raise UnsafeImageURLError("Image URL targets a prohibited network address.")
    else:
        if _looks_like_numeric_host(host):
            raise UnsafeImageURLError("Image URL host is an ambiguous numeric address.")
        if host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_SUFFIXES):
            raise UnsafeImageURLError("Image URL targets an internal host name.")
        if "." not in host:
            raise UnsafeImageURLError("Image URL host must be a fully qualified public name.")
        try:
            host.encode("idna")
        except UnicodeError as exc:
            raise UnsafeImageURLError("Image URL host is not a valid host name.") from exc

    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return ValidatedImageURL(url=url, host=host, port=port or 443, path_and_query=path)


def _resolve_public_addresses(host: str, port: int) -> list[str]:
    """Resolve ``host`` and require EVERY address to be globally routable."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError) as exc:
        raise ImageFetchError("Image host could not be resolved.") from exc
    addresses: list[str] = []
    for info in infos:
        raw = info[4][0]
        try:
            ip = ipaddress.ip_address(raw.split("%", 1)[0])
        except ValueError as exc:
            raise UnsafeImageURLError("Image host resolved to an invalid address.") from exc
        if _is_prohibited_ip(ip):
            raise UnsafeImageURLError("Image host resolves to a prohibited network address.")
        if raw not in addresses:
            addresses.append(raw)
    if not addresses:
        raise ImageFetchError("Image host did not resolve to any address.")
    return addresses


def _open_client(connect_timeout: float, read_timeout: float):
    """Build the HTTP client. Isolated so tests can prove it is never reached."""
    import httpx

    return httpx.Client(
        follow_redirects=False,
        trust_env=False,  # never route through an environment proxy that re-resolves DNS
        timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
        headers={"Accept": "image/*", "User-Agent": "lumenai-image-fetch"},
    )


def fetch_image_bytes(
    url: str,
    *,
    max_bytes: int | None = None,
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    read_timeout: float = DEFAULT_READ_TIMEOUT,
) -> bytes:
    """Fetch an image from an allow-listed https host. Fail-closed.

    Raises :class:`UnsafeImageURLError` (including
    :class:`ImageFetchNotPermittedError`) BEFORE any DNS lookup or connection
    when the URL is prohibited or its host is not allow-listed, and
    :class:`ImageFetchError` when a permitted fetch does not yield image bytes.
    """
    target = assert_image_url_allowed(url)
    if target.host not in allowed_fetch_hosts():
        raise ImageFetchNotPermittedError(
            "Remote image retrieval is disabled for this host. Upload the image "
            "bytes, or have an operator allow-list the host."
        )

    limit = int(max_bytes if max_bytes is not None else os.getenv("CV_IMAGE_MAX_BYTES", DEFAULT_MAX_BYTES))
    addresses = _resolve_public_addresses(target.host, target.port)
    pinned = addresses[0]
    netloc = f"[{pinned}]" if ":" in pinned else pinned
    pinned_url = f"https://{netloc}{target.path_and_query}"

    try:
        with _open_client(connect_timeout, read_timeout) as client:
            with client.stream(
                "GET", pinned_url,
                headers={"Host": target.host},
                extensions={"sni_hostname": target.host},
            ) as response:
                if 300 <= response.status_code < 400:
                    raise ImageFetchError("Image URL redirected; redirects are not followed.")
                if response.status_code != 200:
                    raise ImageFetchError(f"Image host returned HTTP {response.status_code}.")
                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > limit:
                    raise ImageFetchError("Image exceeds the maximum permitted size.")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > limit:
                        raise ImageFetchError("Image exceeds the maximum permitted size.")
                    chunks.append(chunk)
    except (UnsafeImageURLError, ImageFetchError):
        raise
    except Exception as exc:  # network / TLS / protocol failure — never leak detail
        raise ImageFetchError("Image could not be retrieved.") from exc

    data = b"".join(chunks)
    if not data:
        raise ImageFetchError("Image host returned an empty body.")
    return data


def try_fetch_image_bytes(url: str) -> bytes | None:
    """Best-effort wrapper: bytes, or ``None`` when the fetch is prohibited,
    not permitted, or failed. Never raises and never falls back to an
    unvalidated request."""
    try:
        return fetch_image_bytes(url)
    except (UnsafeImageURLError, ImageFetchError):
        return None
