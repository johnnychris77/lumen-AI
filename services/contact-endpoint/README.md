# LumenAI Contact Endpoint

A tiny, dependency-free Node service that receives demo-request submissions from
the public marketing site (`lumenai.opsbridgesolution.com`) and forwards them to an
operator-owned destination. It is deployed as a **separate Render Web Service**
and is **not** part of the LumenAI application backend — it shares no database,
auth, or PHI with the product.

## What it does

`POST /` (JSON) — accepts the marketing contact form payload, validates it,
drops honeypot/spam, and forwards a clean JSON object to
`CONTACT_FORWARD_WEBHOOK`. `GET /health` reports liveness + whether a
destination is configured.

## Security

- **No secrets in source.** The delivery destination is the
  `CONTACT_FORWARD_WEBHOOK` env var only.
- **Not an open relay.** The destination is fixed by env; a submitter can't
  choose recipients. Only a bounded, validated JSON body is accepted.
- **CORS locked** to `CONTACT_ALLOWED_ORIGIN` (default `https://lumenai.opsbridgesolution.com`).
- Honeypot (`company_website`) submissions are accepted-and-dropped.
- Per-IP rate limiting, 16 KB body cap, and **no PII in logs** (only the
  reference id and interest category are logged).

## Environment variables

| Var | Required | Default | Purpose |
|---|---|---|---|
| `PORT` | — | `8080` | Set automatically by Render. |
| `CONTACT_ALLOWED_ORIGIN` | — | `https://lumenai.opsbridgesolution.com` | Only origin allowed to POST. |
| `CONTACT_FORWARD_WEBHOOK` | **yes** | *(none)* | Operator-owned inbound webhook that receives the submission JSON (e.g. a Slack incoming webhook, a Zapier/Make catch hook, or your email service's inbound endpoint). Until set, the endpoint returns `501` and the site stays in mock mode. Set it in the Render dashboard — never commit it. |

## Local run

```bash
cd services/contact-endpoint
CONTACT_FORWARD_WEBHOOK="https://example.com/your-hook" \
CONTACT_ALLOWED_ORIGIN="http://localhost:5173" \
node server.mjs
# POST http://localhost:8080/ with the contact JSON
```

## Deploy (Render)

Defined as a service in the repo-root `render.yaml` blueprint. See
`docs/marketing/DEPLOYMENT_GUIDE.md` for the full walkthrough. After it deploys,
copy its URL into the marketing static site's `VITE_CONTACT_ENDPOINT` env var so
the form switches from mock mode to live delivery.

## Forwarded payload shape

```json
{
  "reference": "LMN-<base36 id>",
  "source": "lumenai-marketing",
  "receivedAt": "ISO-8601",
  "name": "…", "organization": "…", "role": "…",
  "email": "…", "interest": "Request a demonstration", "message": "…"
}
```
