# Illustrative RPM scenarios

RPM is owner-only YouTube Studio data. This package does not estimate RPM from public data and does
not claim that any range is an industry average.

The versioned assumptions live in `rpm_scenarios.json`. They are user-selectable modeling inputs:

| Profile | Geography assumption | USD range per 1,000 views | Source type |
|---|---|---:|---|
| `general_user_assumption` | Mixed global audience | 1.00–8.00 | `user_assumption` |
| `tier1_user_assumption` | Primarily Tier-1 audience | 3.00–18.00 | `user_assumption` |
| `shorts_user_assumption` | Mixed global Shorts feed | 0.01–0.20 | `user_assumption` |

Each profile records currency, geography assumption, effective date, uncertainty range,
`source_type`, and nullable `source_url`. The current profiles deliberately use
`source_type=user_assumption` and `source_url=null`; no third-party attribution is implied.

Call `estimate_rpm(..., scenario_profile="general_user_assumption")` to select a packaged
assumption, or provide `scenario_override=(low, high)` for a caller-owned assumption. Without
either input, the response has `estimable=False`, `scenario=None`, and no numeric range. Do not
apply a current scenario range to historical lifetime views as a revenue estimate.
