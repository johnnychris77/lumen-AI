# Emerging Trend Detection

## Tenant-scoped, not network-scoped

`oracle_trend_detection_service.detect_finding_rate_trend` works directly
off one tenant's own `InspectionFinding` history -- a plain two-window
comparison (a recent `window_days`-long window vs. the equal-length window
before it), with no peer-tenant enrollment precondition.

This is deliberately independent of Horizon's network-wide
`EmergingTrendAlert` (`horizon_trend_detection_service.detect_emerging_trends`),
which requires `horizon_participation_service.list_enrolled_tenant_ids` to
return at least `EARLY_WARNING_K` peer tenants -- a single-tenant deployment
would get nothing from that path. Oracle's trend detection never merges
with or re-derives Horizon's algorithm; a hypothesis may *cite* a Horizon
`EmergingTrendAlert` id as supporting evidence, nothing more.

## What the numbers mean

`direction` is `increasing` / `decreasing` / `stable` / `volatile`, derived
from the percentage change between the two windows (`>15%` /  `<-15%` /
otherwise). `statistical_confidence` is only ever `low` or `moderate` --
never a claim of statistical significance -- and is paired with the raw
`data_points_json` (`{window, start, end, count}` for both windows) so a
reviewer can see exactly what produced the classification.

## Promoting a trend to a hypothesis

`oracle_trend_detection_service.promote_to_hypothesis` creates an
`OracleHypothesis` from a trend observation, copying `trend_category` into
`discovery_category` and prefilling `hypothesis_statement` with an
association-only phrasing if the caller doesn't supply one. A trend can
only be promoted once (`promoted_to_hypothesis_id` guards against a second
promotion).
