# Executive analytics report

## Evidence status

No authentic GA4 extract has been retrieved in this environment. Consequently, no real store funnel, retention, revenue or traffic-source finding is reported. The first working workflow is demonstrated with a small synthetic software fixture. Its calculated results and provenance are in `data/processed/fixture/findings.md` and `manifest.json`.

## Observed workflow checks — synthetic only

The fixture deliberately contains shared session IDs across users, a purchase with an out-of-order cart, repeat activity, and missing identity. Review the generated report for calculated counts. These cases illustrate why event counts, purchase-session rate and strict funnel conversion answer different questions. They are not estimates of Google Merchandise Store performance.

## Independent simulated experiment

The calculated seed-42 simulation (20,000 synthetic users) yielded control conversion 7.215% and treatment conversion 8.110%, an absolute difference of 0.895 percentage points. The 95% Newcombe interval is [0.158, 1.633] percentage points; the two-sided pooled z-test p-value is 0.01737. The mobile-adjusted treatment odds ratio is 1.136 (95% CI 1.024–1.261). These are simulation results only, not evidence of an actual store improvement. See `data/processed/experiment/results.json` for full precision. The prospective planning example requires rounding up to 5,561 users per arm.

A fixed-seed data-generating model assigns treatment independently with probability .5 and simulates mobile mix and conversion. Its treatment coefficient is an assumption, not a measured improvement.

The primary estimand is treatment minus control conversion probability. The two-proportion pooled z-test is two-sided at .05; a Newcombe 95% interval expresses uncertainty in the absolute risk difference. Logistic regression adjusts for the pre-treatment synthetic mobile indicator; its odds ratio is conditional and must not be read as relative conversion lift. Independent users, binary outcomes and adequate group counts are assumed. The simulation has no spillovers, repeated exposure, missing outcomes or sample-ratio monitoring issues; a real experiment needs checks for these.

Prospective power uses an illustrative control rate 8%, target 9.5%, equal allocation, alpha .05 and 80% power. The calculated per-arm size is a planning example based on a normal approximation. It is not post-hoc observed power and is not tailored to the synthetic model's marginal baseline. Pre-register a business-relevant minimum effect, duration and guardrails; use fixed-horizon evaluation or a valid sequential method. A small p-value alone does not justify rollout.

## Assumptions and limitations

GA4 pseudonyms are not people. First observed month is not true acquisition. The three-month source is obfuscated with placeholder values and limited consistency. Missing identity, incomplete instrumentation, time ties, boundary sessions and extraction gaps can alter conversion. Cohort month zero is tautological and incomplete months cannot support mature retention comparisons. First-user source is not session attribution. These data cannot identify causal UX effects or profit.

## Recommendations and next review

First obtain and reconcile the bounded authentic export, audit schema/missingness and compare SQL and Python funnels. Then expand to the full window, validate coverage, and examine absolute stage loss and device/source denominators. Investigate instrumentation before attributing loss to UX. Propose a real randomized experiment only after selecting a specific intervention, business threshold and guardrails. Build and reconcile the Power BI report before publishing screenshots or numerical portfolio claims.

Source caveats: [Google public sample documentation](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset).
