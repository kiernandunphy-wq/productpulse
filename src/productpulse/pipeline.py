"""CLI: python -m productpulse.pipeline --input FILE --label fixture|ga4 --output DIR."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from .cleaning import clean_events
from .analytics import session_table, funnel_table, retention_table
from .experiment import simulate, analyze


def run(input_path, output, label):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Explicit string dtypes preserve identifiers and dates across CSV exports.
    raw = pd.read_csv(input_path, dtype="string")
    events, quality = clean_events(raw)
    sessions = session_table(events)
    funnel = funnel_table(sessions)
    tables = {"sessions": sessions, "funnel": funnel, "retention": retention_table(events),
              "event_counts": events.groupby("event_name").size().rename("events").reset_index()}
    for name, keys in [("daily", ["session_date"]), ("traffic", ["source", "medium"]),
                       ("segments", ["device_category"])]:
        table = sessions.groupby(keys).agg(sessions=("ga_session_id", "size"),
            purchasers=("any_purchase", "sum"), ordered_purchases=("purchase", "sum")).reset_index()
        table["purchase_session_rate"] = table.purchasers / table.sessions
        tables[name] = table
    tables["descriptive"] = sessions[["events"]].describe().reset_index(names="statistic")
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False)
    manifest = {"dataset_label": label, "input_sha256": hashlib.sha256(Path(input_path).read_bytes()).hexdigest(),
                "quality": quality, "eligible_sessions": len(sessions),
                "date_min": str(events.event_date.min()), "date_max": str(events.event_date.max()),
                "funnel_policy": "strict timestamps, ordered within user/session; tied timestamps do not advance",
                "pandas_version": pd.__version__}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(funnel.stage, funnel.sessions)
    ax.set(title=f"ProductPulse — {label.upper()} data", ylabel="Ordered sessions")
    fig.tight_layout()
    fig.savefig(output / "funnel.png", dpi=160)
    plt.close(fig)
    report = f"""# Calculated workflow report: {label.upper()}

Input rows: {len(events)}. Eligible sessions: {len(sessions)}.
Excluded event rows with missing user/session: {quality['excluded_session_rows']}.
Ordered stage counts: {dict(zip(funnel.stage, funnel.sessions))}.

These results describe only this input. Fixture results are synthetic software checks.
Session purchase rate counts any purchase; strict funnel conversion requires all four stages.
No causal or business improvement claim is supported by these counts.
Inspect manifest.json and retention completeness before interpretation.
"""
    (output / "findings.md").write_text(report, encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True, choices=["fixture", "ga4"])
    parser.add_argument("--experiment-output", default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output, args.label), indent=2))
    if args.experiment_output:
        directory = Path(args.experiment_output)
        directory.mkdir(parents=True, exist_ok=True)
        experiment = simulate()
        experiment.to_csv(directory / "simulated_assignments.csv", index=False)
        (directory / "results.json").write_text(json.dumps(analyze(experiment), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
