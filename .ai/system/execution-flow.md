# LumenAI Execution Flow

## Standard Issue Flow
1. Read issue
2. Map issue to owning agent
3. Architect clarifies constraints
4. Builder agent implements
5. Reviewer agent audits
6. QA agent validates
7. Release agent documents impact

## Agent Routing
- backend changes -> Backend Agent
- UI changes -> Frontend Agent
- model/inference changes -> ML Agent
- CI/CD/runtime changes -> DevOps Agent
- cross-cutting or refactor work -> Architect Agent first

## Required Outputs Per Task
- changed files summary
- rationale
- validation notes
- risks
- follow-up recommendations if needed
