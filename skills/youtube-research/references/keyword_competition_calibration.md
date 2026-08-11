# Keyword competition calibration

The runtime validates artifacts against `keyword_competition_calibration.schema.json` using JSON
Schema Draft 2020-12 and then applies semantic checks.

A production artifact must:

- use a semantic version accepted by the schema;
- declare at least 200 training queries and at least 50 holdout queries;
- provide the same non-empty feature names in `required_features`, `coefficients`, and
  `feature_transforms`;
- use only finite coefficients, intercept, thresholds, and holdout metrics;
- use strictly increasing thresholds within 0–100 with unique non-empty labels;
- provide a non-empty dataset ID, a lowercase 64-character SHA-256 digest, an ISO date-time,
  methodology, label definition, and holdout metrics;
- keep any provenance `training_query_count` consistent with the top-level count.

No competition score is returned when schema, semantics, or provenance validation fails. A valid
artifact still yields no score if required runtime features are unavailable.

Versions beginning with `test-` are accepted only when the repository is created with explicit
test mode enabled. Test mode is deterministic test infrastructure, not a production bypass.
