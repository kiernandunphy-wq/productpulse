"""Separate synthetic experiment; no GA4 treatment assignments are implied."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep, proportion_effectsize
from statsmodels.stats.power import NormalIndPower


def simulate(seed=42, n=20000):
    rng = np.random.default_rng(seed)
    treatment = rng.binomial(1, .5, n)
    mobile = rng.binomial(1, .6, n)
    probability = 1 / (1 + np.exp(-(-2.45 + .18*treatment - .25*mobile)))
    return pd.DataFrame({"user_id": np.arange(n), "treatment": treatment,
                         "mobile": mobile, "converted": rng.binomial(1, probability)})


def analyze(df):
    groups = df.groupby("treatment").converted.agg(["sum", "count", "mean"])
    c, t = groups.loc[0], groups.loc[1]
    z, p = proportions_ztest([t["sum"], c["sum"]], [t["count"], c["count"]])
    low, high = confint_proportions_2indep(int(t["sum"]), int(t["count"]),
        int(c["sum"]), int(c["count"]), method="newcomb", compare="diff", alpha=.05)
    fit = sm.Logit(df.converted, sm.add_constant(df[["treatment", "mobile"]])).fit(disp=False)
    ci = fit.conf_int().loc["treatment"]
    required = NormalIndPower().solve_power(effect_size=abs(proportion_effectsize(.095, .08)),
                                            alpha=.05, power=.8, ratio=1)
    return {"label": "SIMULATED ONLY", "n": len(df), "control_rate": float(c["mean"]),
            "treatment_rate": float(t["mean"]), "absolute_difference": float(t["mean"]-c["mean"]),
            "ci95_newcombe": [float(low), float(high)], "z": float(z), "p_two_sided": float(p),
            "adjusted_treatment_odds_ratio": float(np.exp(fit.params["treatment"])),
            "adjusted_or_ci95": np.exp(ci).tolist(),
            "planned_n_per_arm_8_to_9_5_percent": float(required)}
