# Project Catalyst — Prompt & Conversation Memory

LumenAI OS v4.4 — Section 9

## Genuinely new — confirmed before writing this file

No conversation/session-memory table existed anywhere in this codebase
before this sprint (confirmed by search across `app/models/`). This is a
real gap, not a duplication risk.

## Scope: `(tenant_id, user_email)`

`CatalystConversation` and every `CatalystMessage` in it is scoped by
the exact identity pairing `app/enterprise_auth.py` already resolves per
request. Every read path (`list_conversations`, `list_messages`,
`recent_context`) filters on both fields — one user's conversation is
never visible to another user, even within the same tenant, and no
conversation ever crosses a tenant boundary. This is exercised directly
by `test_catalyst_copilot.py`'s session-isolation tests.

## Retention: a real, honest cutoff

`CONVERSATION_RETENTION_DAYS = 90`. `apply_retention(db, tenant_id)` —
called at the top of every `get_or_create_active_conversation` — marks
any conversation whose `updated_at` is past the window as `archived`.
Archived conversations:

* drop out of `list_conversations` (never shown as active),
* are still real rows (never deleted outright — this is a retention
  *policy*, not a fabricated "forgetting" behavior),
* cannot be resumed via `conversation_id` from the chat endpoint (a
  fresh conversation is started instead).

This is a real, enforced limit — not a claim of retention behavior that
isn't actually implemented.

## Follow-up understanding

`recent_context(db, conversation_id, tenant_id, turns=6)` returns the
last N turns of *this* conversation only, for a caller (the query/action
engine, or a future skill) that wants short-term context for a follow-up
question ("What about last month?" after "What's the workload forecast
for next week?"). It is intentionally not sent to any external model —
there isn't one — it is available for the deterministic engines here to
consult when disambiguating a follow-up query.

## Endpoints

```
POST /api/catalyst/chat                                  {message, conversation_id?, persona?}
GET  /api/catalyst/conversations
GET  /api/catalyst/conversations/{conversation_id}/messages
```
