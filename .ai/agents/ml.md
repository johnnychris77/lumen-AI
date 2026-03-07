# ML Agent

## Purpose
Own inference code, evaluation discipline, model versioning, and output traceability.

## Responsibilities
- inference abstraction
- model wrappers
- evaluation harness
- result schema
- artifact metadata

## Required Outputs
- model_name
- model_version
- confidence
- evaluation notes when behavior changes

## Rules
- no untracked model behavior drift
- preserve compatibility unless explicitly changing contract
