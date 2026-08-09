/**
 * LumenAI marketing contact endpoint.
 *
 * A tiny, dependency-free Node service that receives demo-request submissions
 * from the public marketing site (lumenai.opsbridgesolution.com) and forwards them to an
 * operator-owned destination. Deployed as a separate Render Web Service — it is
 * NOT part of the frozen application backend and shares no data with it.
 *
 * Security posture (matches docs/marketing constraints):
 *  - No secrets in source. The forwarding destination is read from the
 *    CONTACT_FORWARD_WEBHOOK env var only.
 *  - Not an open mail relay: the destination is fixed by env; the submitter
 *    cannot choose a recipient. Only a bounded, validated JSON body is accepted.
 *  - CORS is locked to CONTACT_ALLOWED_ORIGIN (the marketing domain).
 *  - Honeypot (`company_website`) submissions are accepted-and-dropped.
 *  - Best-effort per-IP rate limiting; body size capped; no PII in logs.
 *
 * Env:
 *  - PORT                     (Render sets this)
 *  - CONTACT_ALLOWED_ORIGIN   e.g. https://lumenai.opsbridgesolution.com  (default below)
 *  - CONTACT_FORWARD_WEBHOOK  operator-owned inbound webhook (Slack/Zapier/
 *                             email-service/etc.) that receives the JSON.
 *                             REQUIRED — without it the endpoint returns 501.
 */
import http from "node:http";

const PORT = Number(process.env.PORT) || 8080;
const ALLOWED_ORIGIN = process.env.CONTACT_ALLOWED_ORIGIN || "https://lumenai.opsbridgesolution.com";
const FORWARD_WEBHOOK = process.env.CONTACT_FORWARD_WEBHOOK || "";
const MAX_BODY_BYTES = 16 * 1024;

const AREAS_OF_INTEREST = new Set([
  "Request a demonstration",
  "Discuss a pilot",
  "Join the product-validation program",
  "Partnership / investment",
  "General question",
]);

// ── Best-effort in-memory rate limit (per IP, sliding window) ────────────────
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 5;
/** @type {Map<string, number[]>} */
const hits = new Map();
function rateLimited(ip) {
  const now = Date.now();
  const arr = (hits.get(ip) || []).filter((t) => now - t < WINDOW_MS);
  arr.push(now);
  hits.set(ip, arr);
  if (hits.size > 5000) hits.clear(); // crude memory bound
  return arr.length > MAX_PER_WINDOW;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function corsHeaders() {
  // Always advertise ONLY the configured marketing origin — never reflect an
  // arbitrary request Origin. A browser blocks any other origin's fetch.
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function send(res, status, origin, body) {
  res.writeHead(status, { "Content-Type": "application/json", ...corsHeaders(origin) });
  res.end(JSON.stringify(body));
}

function validate(v) {
  if (typeof v !== "object" || v === null) return "Invalid payload.";
  const str = (x) => (typeof x === "string" ? x.trim() : "");
  if (str(v.name).length < 2) return "name";
  if (str(v.organization).length < 2) return "organization";
  if (str(v.role).length < 2) return "role";
  if (!EMAIL_RE.test(str(v.email))) return "email";
  if (!AREAS_OF_INTEREST.has(v.interest)) return "interest";
  if (v.consent !== true) return "consent";
  if (typeof v.message === "string" && v.message.length > 2000) return "message";
  return null;
}

const server = http.createServer((req, res) => {
  const origin = req.headers.origin || "";

  if (req.method === "OPTIONS") {
    res.writeHead(204, corsHeaders(origin));
    return res.end();
  }
  if (req.method === "GET" && req.url === "/health") {
    return send(res, 200, origin, { ok: true, configured: Boolean(FORWARD_WEBHOOK) });
  }
  if (req.method !== "POST") {
    return send(res, 405, origin, { ok: false, error: "Method not allowed." });
  }

  const ip = (req.headers["x-forwarded-for"]?.toString().split(",")[0].trim()) || req.socket.remoteAddress || "unknown";
  if (rateLimited(ip)) {
    return send(res, 429, origin, { ok: false, error: "Too many requests — please try again shortly." });
  }

  let raw = "";
  let tooBig = false;
  req.on("data", (chunk) => {
    raw += chunk;
    if (raw.length > MAX_BODY_BYTES) {
      tooBig = true;
      req.destroy();
    }
  });
  req.on("end", async () => {
    if (tooBig) return send(res, 413, origin, { ok: false, error: "Payload too large." });

    let data;
    try {
      data = JSON.parse(raw || "{}");
    } catch {
      return send(res, 400, origin, { ok: false, error: "Invalid JSON." });
    }

    // Honeypot: accept-and-drop, never forward.
    if (typeof data.company_website === "string" && data.company_website.length > 0) {
      return send(res, 200, origin, { ok: true, reference: data.reference || "IGNORED" });
    }

    const bad = validate(data);
    if (bad) return send(res, 400, origin, { ok: false, error: `Invalid field: ${bad}` });

    if (!FORWARD_WEBHOOK) {
      // Fail loud so the operator knows to configure the destination.
      console.error("[contact] CONTACT_FORWARD_WEBHOOK is not set — cannot deliver.");
      return send(res, 501, origin, { ok: false, error: "Contact delivery is not configured yet." });
    }

    const reference = typeof data.reference === "string" ? data.reference : `LMN-${Date.now().toString(36).toUpperCase()}`;
    const payload = {
      reference,
      source: "lumenai-marketing",
      receivedAt: new Date().toISOString(),
      name: String(data.name).trim(),
      organization: String(data.organization).trim(),
      role: String(data.role).trim(),
      email: String(data.email).trim(),
      interest: data.interest,
      message: typeof data.message === "string" ? data.message.trim() : "",
    };

    try {
      const fwd = await fetch(FORWARD_WEBHOOK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!fwd.ok) {
        console.error(`[contact] forward failed status=${fwd.status} ref=${reference}`);
        return send(res, 502, origin, { ok: false, error: "Delivery failed — please email us directly." });
      }
      // Log reference + interest only — no PII.
      console.log(`[contact] delivered ref=${reference} interest="${payload.interest}"`);
      return send(res, 200, origin, { ok: true, reference });
    } catch (err) {
      console.error(`[contact] forward error ref=${reference}:`, err?.message || err);
      return send(res, 502, origin, { ok: false, error: "Delivery error — please try again." });
    }
  });
});

server.listen(PORT, () => {
  console.log(`[contact] listening on :${PORT} — origin=${ALLOWED_ORIGIN} configured=${Boolean(FORWARD_WEBHOOK)}`);
});
