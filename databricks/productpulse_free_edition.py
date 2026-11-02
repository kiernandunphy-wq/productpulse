# Databricks notebook source
# MAGIC %md
# MAGIC # ProductPulse — SYNTHETIC fixture demonstration
# MAGIC Import as a Python notebook and use serverless compute. No Google credentials required.
# MAGIC Platform execution is not yet verified. Use a bounded authentic CSV to analyze GA4.

# COMMAND ----------
import pandas as pd
from io import StringIO

# COMMAND ----------
"""Validate the flat event contract; never silently deduplicate GA4 events."""
import pandas as pd

REQUIRED = {"event_date", "event_timestamp", "event_name", "user_pseudo_id",
            "ga_session_id", "source", "medium", "device_category"}


def clean_events(frame):
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    df = frame.copy()
    for col in ["user_pseudo_id", "source", "medium", "device_category", "event_name"]:
        df[col] = df[col].astype("string").str.strip().replace(
            {"": pd.NA, "<Other>": pd.NA, "(not set)": pd.NA})
    df["event_date"] = pd.to_datetime(df.event_date.astype(str), format="%Y%m%d", errors="coerce")
    for col in ["event_timestamp", "ga_session_id"]:
        numeric = pd.to_numeric(df[col], errors="coerce")
        if ((numeric.dropna() % 1) != 0).any():
            raise ValueError(f"{col} must contain integers")
        df[col] = numeric.astype("Int64")
    if df.event_date.isna().any() or df.event_timestamp.isna().any() or df.event_name.isna().any():
        raise ValueError("Invalid event date, timestamp, or event name")
    if (df.event_timestamp <= 0).any() or (df.ga_session_id.dropna() < 0).any():
        raise ValueError("Invalid timestamp or session ID")
    quality = {"input_rows": len(df), "missing_user_rows": int(df.user_pseudo_id.isna().sum()),
               "missing_session_rows": int(df.ga_session_id.isna().sum()),
               "exact_duplicate_rows": int(df.duplicated().sum())}
    df["eligible_session"] = df.user_pseudo_id.notna() & df.ga_session_id.notna()
    quality["excluded_session_rows"] = int((~df.eligible_session).sum())
    for col in ["source", "medium", "device_category"]:
        df[col] = df[col].fillna("Unknown")
    return df, quality

# COMMAND ----------
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

# COMMAND ----------
raw = pd.read_csv(StringIO('event_date,event_timestamp,event_name,user_pseudo_id,ga_session_id,source,medium,device_category\n20201101,1604188800000000,page_view,u1,1,google,organic,desktop\n20201101,1604188801000000,view_item,u1,1,google,organic,desktop\n20201101,1604188802000000,add_to_cart,u1,1,google,organic,desktop\n20201101,1604188803000000,purchase,u1,1,google,organic,desktop\n20201101,1604188800000000,page_view,u2,1,direct,none,mobile\n20201101,1604188801000000,view_item,u2,1,direct,none,mobile\n20201101,1604188800000000,add_to_cart,u3,2,google,organic,mobile\n20201101,1604188801000000,page_view,u3,2,google,organic,mobile\n20201101,1604188802000000,view_item,u3,2,google,organic,mobile\n20201101,1604188803000000,purchase,u3,2,google,organic,mobile\n20201201,1606780800000000,page_view,u1,3,google,organic,desktop\n20201201,1606780801000000,view_item,u1,3,google,organic,desktop\n20201201,1606780802000000,add_to_cart,u1,3,google,organic,desktop\n20201201,1606780803000000,purchase,u1,3,google,organic,desktop\n20201201,1606780800000000,page_view,,4,<Other>,,mobile\n20201201,1606780800000000,page_view,u4,,,email,desktop\n'), dtype='string')
events, quality = clean_events(raw)
sessions = session_table(events)
print(quality)
display(funnel_table(sessions))
display(retention_table(events))
assert funnel_table(sessions).sessions.tolist() == [4, 4, 2, 2]
