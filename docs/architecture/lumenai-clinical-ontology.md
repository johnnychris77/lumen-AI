# LumenAI Clinical Ontology

Every database model, API response, AI output, report, dashboard, and
training dataset in LumenAI should map back to this chain. If a piece of
data can't be placed on this chain, it either belongs in a different
system or the ontology needs a deliberate, documented extension — it
should never be bolted on as a disconnected field.

```
Instrument
    ↓
Instrument Family
    ↓
Manufacturer
    ↓
Model
    ↓
Anatomy
    ↓
Inspection Zone
    ↓
Finding
    ↓
Severity
    ↓
SPD Risk
    ↓
Clinical Interpretation
    ↓
Recommendation
    ↓
Supervisor Decision
    ↓
Learning Signal
```

## Link-by-link, with the code that owns each step

| Ontology step | What it answers | Owning code |
|---|---|---|
| **Instrument** | What physical object is being inspected? | `app/models/inspection.py` (`instrument_type`), `app/models/instrument_registry.py` |
| **Instrument Family** | What class of instrument is it (forceps, rigid scope, drill bit, …)? | `app/services/instrument_anatomy.py::resolve_family` |
| **Manufacturer** | Who made it? | `app/models/manufacturer_reg.py`, `Inspection.vendor_name` |
| **Model** | Which specific model/UDI? | `app/models/baseline_library.py` (`model_name`, `udi`) |
| **Anatomy** | What are this family's zones, high-risk areas, required views? | `app/services/instrument_anatomy.py::anatomy_profile` |
| **Inspection Zone** | Which specific zone is a finding located in? | `app/services/instrument_zones.py::zone_fields` |
| **Finding** | What was observed (blood, crack, missing component, …)? | `app/services/baseline_comparison_scoring_service.py` (`predicted_findings`) |
| **Severity** | How significant is the finding? | Per-finding `severity_index` / `severity` fields; `app/services/pilot_validation_service.py::severity_from_risk_score` |
| **SPD Risk** | Is this zone/finding combination high-retention / high-risk? | `app/services/instrument_zones.py::is_high_retention`, `HIGH_RETENTION_ZONES` |
| **Clinical Interpretation** | What does this mean, in plain SPD language? | `app/services/clinical_mentor.py::ai_mentor` |
| **Recommendation** | What should happen to the instrument? | `app/services/baseline_comparison_scoring_service.py` (`ai_clinical_review`, `_ACTION_TEXT`) |
| **Supervisor Decision** | What did a human actually decide? | `app/models/supervisor_review.py` |
| **Learning Signal** | Does this become labeled data for the model? | `app/models/pilot_validation.py` (ground-truth label), `app/models/model_registry.py` / `shadow_prediction.py`, `app/models/retained_image.py` |

## Rules for using the ontology

1. **No skipping links.** A finding without a resolved zone, and a zone
   without a resolved anatomy/family, is an incomplete record — not a
   simplification. It should be flagged (e.g. Phase 18's
   `missing_required_zones` safety-queue bucket), not silently accepted.
2. **Downstream always cites upstream.** A dashboard metric that reports
   on "findings by zone" is only meaningful because the finding is
   traceable through zone → anatomy → family → instrument. Any new report
   should be checked against this chain before it ships.
3. **The Learning Signal step is the return path.** Continuous learning
   (Layer 9 of the architecture) is not a separate concern bolted onto the
   ontology — it *is* the ontology's last link. A supervisor decision that
   doesn't produce a learning signal is a missed opportunity, and a
   learning signal without a traceable supervisor decision behind it is
   not trustworthy ground truth.
4. **New AI capabilities attach to an existing link, or extend the chain
   deliberately.** For example, a future segmentation/heatmap capability
   (Architecture Roadmap Stage 7–8) attaches to the **Finding** and
   **Inspection Zone** links — it does not introduce a parallel,
   disconnected localization system.
