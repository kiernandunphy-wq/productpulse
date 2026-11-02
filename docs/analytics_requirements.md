# Analytical requirements

Stakeholders: product manager (journey friction), ecommerce lead (purchase activity), acquisition analyst (source mix), BI consumer (consistent measures). These are project roles, not interviews claimed to have occurred.

| ID | Business question / output | Acceptance criterion |
|---|---|---|
| R1 | Can exported events be trusted? | Required fields validated; malformed dates/timestamps fail; missing identity and duplicates counted; export row count reconciled manually |
| R2 | Where does the recorded journey narrow? | Ordered session funnel is non-increasing; same-session and out-of-order cases tested; SQL/Python parity required on real export |
| R3 | What browsing and product activity is recorded? | All event counts retained; item-grain SQL separated from session counts; no revenue claim from quantity |
| R4 | Which acquisition/device groups differ? | Source/medium and device tables include denominator and purchase sessions; descriptive association only |
| R5 | Do observed users return? | Monthly observed-first-activity cohort denominator fixed; absent mature cells zero, future cells absent; incomplete months disclosed |
| R6 | What would an experiment decision require? | Fixed-seed synthetic assignments separated; absolute effect, two-sided test, CI, adjusted odds ratio and prospective power documented |
| R7 | Can stakeholders consume results? | BI CSVs, dictionary, report and import instructions provided; dashboard verification remains separate |

Decision policy: validate instrumentation before proposing UX changes. Identify the largest absolute stage loss and assess segment sample sizes. An observational funnel does not establish a cause. Do not declare a winning experiment based on p-value alone: define minimum useful effect, cost, guardrails and stopping rule before launch.

Scope: initial batch workflow, pandas suitable for an exported subset. No production orchestration, live integration, actual randomized GA4 experiment or React app. Retention means return activity, not subscription retention. Purchaser segment is a session purchase flag; device is a descriptive session segment, not a durable customer demographic.
