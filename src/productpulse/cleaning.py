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
    if not df.event_date.astype('string').str.fullmatch(r'\d{8}', na=False).all():
        raise ValueError("Invalid event date: expected YYYYMMDD")
    df["event_date"] = pd.to_datetime(df.event_date.astype(str), format="%Y%m%d", errors="coerce")
    for col in ["event_timestamp", "ga_session_id"]:
        numeric = pd.to_numeric(df[col], errors="coerce")
        provided = df[col].notna() & df[col].astype('string').str.strip().ne('')
        if (provided & numeric.isna()).any():
            raise ValueError(f"{col} contains nonnumeric values")
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
