# Project Athena — Knowledge Preservation

LumenAI OS v4.8, Section 10.

No exit-interview, video/voice capture, or workflow-recording system
existed anywhere in this codebase before Athena — genuinely new.
`KnowledgePreservationSession` supports the five named capture types:

```
exit_interview | video_capture | voice_transcription | workflow_recording | procedure_demonstration
```

## Never fabricates a capability

`transcript_text` is always human-entered or human-reviewed — this module
never claims to perform real speech-to-text transcription (there is zero
real ML/LLM integration anywhere in this codebase, confirmed repeatedly
across every prior sprint's research). Recording a transcript moves a
session from `captured` to `transcribed`; nothing auto-generates a
transcript from an audio/video reference.

## Converting tacit knowledge into structured knowledge

`convert_to_knowledge_article` promotes a session's transcript (or
summary, if no transcript exists) into a real `KnowledgeArticle` via the
existing `knowledge_repository_service.create_article` — no second
article-creation path. The new article enters the same `draft` →
`pending_review` → `approved` governance workflow as any other
contribution (`docs/athena/institutional-memory.md`, Section 2). The
session records `converted_article_id` and moves to `structured`.

Media (photos/videos captured during the session) attach via the same
`KnowledgeMediaAttachment` table Expert Knowledge Capture and Clinical
Playbooks use, with `source_type="preservation_session"`.

```
POST /api/athena/preservation/sessions
POST /api/athena/preservation/sessions/{id}/media
POST /api/athena/preservation/sessions/{id}/transcript
POST /api/athena/preservation/sessions/{id}/convert
GET  /api/athena/preservation/sessions
GET  /api/athena/preservation/sessions/{id}
```

## Governance and tenant authorization

All Athena routes — including Knowledge Preservation — use
`tenant_authz.require_tenant_roles`, which verifies a real
`TenantMembership` row for the authenticated user before granting access.
This is a deliberate departure from the `_tenant()`/`require_roles()`
pattern used by every prior sprint's routes (Catalyst through Apollo),
which resolves the acting tenant from a client-supplied header with no
membership check — a real cross-tenant authorization gap in those
modules. Athena does not propagate that pattern into an 18th module; the
other 16 modules still need the same retrofit, tracked separately.
