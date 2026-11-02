"""Strict ordered, session-level funnel; observed monthly repeat activity."""
import pandas as pd

STAGES = ["page_view", "view_item", "add_to_cart", "purchase"]


def session_table(events):
    rows = []
    eligible = events[events.eligible_session].sort_values("event_timestamp", kind="stable")
    for (user, session), group in eligible.groupby(["user_pseudo_id", "ga_session_id"], sort=True):
        first = group.iloc[0]
        row = {"user_pseudo_id": user, "ga_session_id": session,
               "session_date": first.event_date.date().isoformat(),
               "source": first.source, "medium": first.medium,
               "device_category": first.device_category, "events": len(group)}
        previous = None
        for stage in STAGES:
            candidates = group.loc[group.event_name.eq(stage), "event_timestamp"]
            if previous is not None:
                candidates = candidates[candidates > previous]
            reached = not candidates.empty and (previous is not None or stage == STAGES[0])
            row[stage] = int(reached)
            previous = int(candidates.min()) if reached else None
            if not reached:
                # A missing prerequisite makes all subsequent steps ineligible.
                for later in STAGES[STAGES.index(stage) + 1:]:
                    row[later] = 0
                break
        row["any_purchase"] = int(group.event_name.eq("purchase").any())
        rows.append(row)
    return pd.DataFrame(rows, columns=["user_pseudo_id", "ga_session_id", "session_date",
                        "source", "medium", "device_category", "events", *STAGES, "any_purchase"])


def funnel_table(sessions):
    counts = [int(sessions[s].sum()) for s in STAGES]
    return pd.DataFrame({"stage": STAGES, "stage_order": range(1, 5), "sessions": counts,
        "rate_from_entry": [n / counts[0] if counts[0] else None for n in counts],
        "rate_from_previous": [1.0 if counts[0] else None] +
        [counts[i] / counts[i-1] if counts[i-1] else None for i in range(1, 4)]})


def retention_table(events):
    active = events.loc[events.user_pseudo_id.notna(), ["user_pseudo_id", "event_date"]].copy()
    if active.empty:
        return pd.DataFrame(columns=["cohort_month", "activity_month", "month_index", "cohort_users", "active_users", "retention_rate"])
    active["month"] = active.event_date.dt.to_period("M")
    active = active[["user_pseudo_id", "month"]].drop_duplicates()
    cohorts = active.groupby("user_pseudo_id").month.min()
    active["cohort"] = active.user_pseudo_id.map(cohorts)
    counts = active.groupby(["cohort", "month"]).user_pseudo_id.nunique()
    rows = []
    for cohort, size in cohorts.value_counts().sort_index().items():
        for month in pd.period_range(cohort, active.month.max(), freq="M"):
            n = int(counts.get((cohort, month), 0))
            rows.append([str(cohort), str(month), month.ordinal-cohort.ordinal, int(size), n, n/size])
    return pd.DataFrame(rows, columns=["cohort_month", "activity_month", "month_index", "cohort_users", "active_users", "retention_rate"])
