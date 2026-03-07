# LumenAI Routing Rules

## Route by change type

### architect
Use first when:
- task spans multiple services
- repo restructuring is needed
- issue is ambiguous
- runtime/design conflict exists

### backend
Use when task changes:
- API routes
- worker jobs
- DB models
- session/engine logic
- queue pipeline
- reporting backend

### frontend
Use when task changes:
- upload UI
- polling UI
- history UI
- report link flow
- dashboards

### ml
Use when task changes:
- inference behavior
- evaluation harness
- model metadata
- prediction schema
- artifacts tied to model output

### devops
Use when task changes:
- Dockerfiles
- docker-compose
- GitHub Actions
- GHCR
- Helm/staging
- metrics and dashboards

### qa-release
Use when task requires:
- validation checklist
- regression confirmation
- release risk summary
- evidence review

## Escalation rule
If a task touches more than one domain, start with architect.
