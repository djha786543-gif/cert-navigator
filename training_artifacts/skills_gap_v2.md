# Skills Gap Analyzer v2 (Production Design)

This v2 artifact is an evolved implementation spec based on:
- `training_artifacts/skills_gap_v1.md` (referenced source artifact; not modified here)
- `certlab-saas-v2.html` reasoning patterns (weighted factor scoring and priority tiers)
- in-repo fallback mirror: `frontend/public/certlab-static.html` lines ~6618-6686

## Extracted core logic from artifact patterns

1. Core scoring logic
- Weighted multi-factor scoring instead of a single boolean match.
- Priority-oriented output: rank items so "what to do next" is explicit.
- Score decomposition concept: total score built from weighted components.

2. Assumptions
- Role readiness is not binary and should be represented on a 0-100 style continuum.
- Skill overlap is a dominant predictor, but not the only predictor.
- Demand-side market signals should influence final priority.

3. Heuristics
- Threshold tiers for actionability (`must apply`, `high priority`, etc.).
- Bonus/penalty adjustments for high-signal factors.
- Prioritization bias toward skills that improve near-term outcomes.

4. Data dependencies
- User profile skill inventory (current level, recency, evidence).
- Role requirement matrix (required level and weight per skill).
- Market demand signal per skill.

## Known v1-style weaknesses and v2 fixes

1. Hardcoded thresholds
- Weakness: rigid cutoffs can overfit.
- v2 fix: central constants + normalized score bands + tunable coefficients.

2. Missing normalization
- Weakness: inconsistent scales (percent vs points vs booleans).
- v2 fix: normalized `[0,1]` fields for proficiency, required level, demand.

3. No confidence scoring
- Weakness: no reliability estimate for downstream decisions.
- v2 fix: confidence from coverage, recency, evidence quality, and requirement completeness.

4. Lack of schema enforcement
- Weakness: free-form objects risk silent drift.
- v2 fix: enforced Pydantic schemas + DB constraints/checks.

## v2 service output contract

```json
{
  "missing_skills": [],
  "priority_order": [],
  "estimated_learning_hours": 0,
  "confidence_score": 0.0
}
```

## v2 production method

For each role requirement:
1. Normalize skill key.
2. Compute effective proficiency = `proficiency * decay(last_used_at)`.
3. Compute skill gap = `max(0, required_level - effective_proficiency)`.
4. Compute priority score =
   `gap * importance_weight * demand_multiplier * critical_multiplier`.
5. Compute estimated hours =
   `ceil(baseline_learning_hours * gap * demand_multiplier)`.
6. Sort descending by `priority_score`.

Confidence score:
- `0.35*coverage + 0.25*recency + 0.20*evidence + 0.15*role_quality + 0.05*gap_density`
- bounded to `[0,1]`.
