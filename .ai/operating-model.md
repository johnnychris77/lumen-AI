# LumenAI Operating Model

## Roles
### Product Owner
John owns prioritization, domain direction, and final approvals.

### Architect
ChatGPT owns system design, engineering OS, issue shaping, and review guidance.

### Builder Agent
Builds scoped issues into PRs.

### Reviewer Agent
Reviews architecture, correctness, maintainability, and hidden risks.

### Release Agent
Handles tags, release notes, image publishing, and deployment promotion.

### ML Agent
Owns evaluation, model quality gates, and regression detection.

## Working Rules
- No direct commits to main for feature work.
- Every issue has acceptance criteria.
- Every PR must explain why, what changed, and how tested.
- Every release must be buildable from GitHub.
