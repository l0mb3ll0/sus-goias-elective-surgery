"""
Generates Figures 1-3 and Table 2 for the SUS elective surgery paper.

Run from the repo root (same directory as sus.py):
    python paper/figures.py

Outputs to paper/:
    fig1_ratio_series.pdf
    fig2_growth_histogram.pdf
    fig3_pre_post_scatter.pdf
    (tab1 removed)
    tab2_falsification.tex
    numbers.json          <- MERGED, not replaced. Keys written by
                             scripts/patch_keys.py and scripts/patch_model_keys.py
                             are preserved. Only keys this script computes are
                             overwritten.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ruptures as rpt

from sus import load, monthly_ratio

OUT = "paper"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "figure.dpi": 200,
})

INK = "#1a1a1a"
ACCENT = "#b3452e"
MUTED = "#8a8a8a"

N = {}  # every number that appears in the prose


# ----------------------------------------------------------------------
# Load. Panel v2 only: same 16,884 rows and 201 facilities as v1, same
# elective total, plus group / comp / *_cnes columns. One panel, one source.
# ----------------------------------------------------------------------
cir = load("all")
el = cir[cir["CAR_INT"] == "01"]
pan = pd.read_parquet("data/interim/hospital_panel_v2.parquet")
pan["any"] = (pan["elec"] + pan["urg"]) > 0

N["n_surgical_rows"] = int(len(cir))
N["n_elective"] = int(len(el))
N["n_hospitals"] = int(el["CNES"].nunique())
N["panel_start"] = str(el["COMPETENCIA"].min())
N["panel_end"] = str(el["COMPETENCIA"].max())

# Clean subset: >=95% month coverage within span, span >=60 months, >=500 elective cases
span = pan[pan["any"]].groupby("CNES")["COMPETENCIA"].agg(["min", "max", "count"])
span["n"] = (pd.PeriodIndex(span["max"], freq="M").asi8
             - pd.PeriodIndex(span["min"], freq="M").asi8 + 1)
vol = pan.groupby("CNES")["elec"].sum()
rel = [c for c in span[(span["count"] / span["n"] >= 0.95) & (span["n"] >= 60)].index
       if vol.get(c, 0) >= 500]
N["n_clean"] = len(rel)
N["clean_share_volume"] = round(float(vol[rel].sum() / vol.sum()), 4)


# ----------------------------------------------------------------------
# Break detection (NOTE index convention: ruptures returns the index at
# which the NEW segment begins, so r.index[i] is the first month of the
# new regime.)
# ----------------------------------------------------------------------
r = monthly_ratio(cir).sort_index()
rc = monthly_ratio(cir[cir["CNES"].isin(rel)]).sort_index()


def breaks(series, pen=1.0):
    b = rpt.Pelt(model="rbf").fit(series.values).predict(pen=pen)
    return [series.index[i] for i in b[:-1]]


N["breaks_full_pen1"] = breaks(r["ratio"], 1.0)
N["breaks_full_pen2"] = breaks(r["ratio"], 2.0)
N["breaks_clean_pen1"] = breaks(rc["ratio"], 1.0)
N["breaks_clean_pen05"] = breaks(rc["ratio"], 0.5)

# Regime means for the text
REGIMES = [("2019-01", "2020-03"), ("2020-04", "2020-08"), ("2020-09", "2022-02"),
           ("2022-03", "2022-08"), ("2022-09", "2023-07"), ("2023-08", "2025-03"),
           ("2025-04", "2025-12")]
N["regime_means"] = {
    f"{a}..{b}": {
        "elec_per_month": round(float(r.loc[a:b, "elec"].mean()), 1),
        "urg_per_month": round(float(r.loc[a:b, "urg"].mean()), 1),
        "ratio": round(float(r.loc[a:b, "elec"].sum() / r.loc[a:b, "urg"].sum()), 3),
    }
    for a, b in REGIMES
}


# ----------------------------------------------------------------------
# FIGURE 1: ratio series with breaks
# ----------------------------------------------------------------------
MARK = ["2020-04", "2022-03", "2022-09", "2023-08", "2025-04"]
LABELS = {"2020-04": "COVID-19", "2022-03": "wave 1", "2022-09": "wave 2",
          "2023-08": "Aug 2023", "2025-04": "Apr 2025"}

fig, ax = plt.subplots(figsize=(6.5, 3.0))
x = np.arange(len(r))
ax.plot(x, r["ratio"].values, color=INK, lw=1.0)

i1 = list(r.index).index("2022-03")
i2 = list(r.index).index("2022-09")
ax.axvspan(i1, i2, color=ACCENT, alpha=0.10, lw=0)
ax.annotate("phased transition", xy=((i1 + i2) / 2, 0.06), xycoords=("data", "axes fraction"),
            fontsize=6, color=ACCENT, ha="center", va="bottom")

YPOS = {"2020-04": 0.97, "2022-03": 0.84, "2022-09": 0.91,
        "2023-08": 0.97, "2025-04": 0.90}
for m in MARK:
    i = list(r.index).index(m)
    if m not in ("2022-03", "2022-09"):
        ax.axvline(i, color=ACCENT, lw=0.7, ls="--", alpha=0.8)
    left = m == "2025-04"          # last boundary: label to the left of its line, clear of the series end
    ax.annotate(LABELS[m], xy=(i - 0.8 if left else i + 0.8, YPOS[m]), xycoords=("data", "axes fraction"),
                fontsize=6.5, color=ACCENT, ha="right" if left else "left", va="top")

# regime means as flat segments
for a, b in REGIMES:
    ia, ib = list(r.index).index(a), list(r.index).index(b)
    mu = r.loc[a:b, "elec"].sum() / r.loc[a:b, "urg"].sum()
    ax.plot([ia, ib], [mu, mu], color=MUTED, lw=1.6, alpha=0.75, solid_capstyle="butt")

ticks = [i for i, m in enumerate(r.index) if m.endswith("-01")]
ax.set_xticks(ticks)
ax.set_xticklabels([r.index[i][:4] for i in ticks])
ax.set_ylabel("elective / urgent surgical admissions")
ax.set_xlabel("")
ax.set_xlim(-1, len(r))
ax.margins(y=0.12)
fig.tight_layout()
fig.savefig(f"{OUT}/fig1_ratio_series.pdf", bbox_inches="tight")
plt.close(fig)


# ----------------------------------------------------------------------
# FIGURE 2: growth-ratio histogram, clean subset
# ----------------------------------------------------------------------
PRE = ("2022-01", "2022-07")
POST = ("2022-08", "2023-06")

pre = pan[pan["CNES"].isin(rel) & pan["COMPETENCIA"].between(*PRE)].groupby("CNES")["elec"].mean()
post = pan[pan["CNES"].isin(rel) & pan["COMPETENCIA"].between(*POST)].groupby("CNES")["elec"].mean()
d = pd.DataFrame({"pre": pre, "post": post}).fillna(0)
d = d[d["pre"] >= 5].copy()
d["ratio"] = d["post"] / d["pre"]

# NOTE: this is the SIH billing field GESTAO, carried on the AIH record.
# It is NOT the CNES establishment field TP_GESTAO used for the
# municipal_at_break / always_state / transferred grouping in section 2.5.
# Similar names, different variables. The legend says SIH explicitly.
d["gestao"] = el.groupby("CNES")["GESTAO"].agg(lambda s: s.mode().iat[0])

N["growth"] = {
    "n": int(len(d)),
    "median": round(float(d["ratio"].median()), 3),
    "mean": round(float(d["ratio"].mean()), 3),
    "p10": round(float(d["ratio"].quantile(0.10)), 3),
    "p25": round(float(d["ratio"].quantile(0.25)), 3),
    "p75": round(float(d["ratio"].quantile(0.75)), 3),
    "p90": round(float(d["ratio"].quantile(0.90)), 3),
    "max": round(float(d["ratio"].max()), 3),
    "share_below_1": round(float((d["ratio"] < 1).mean()), 3),
    "share_above_2": round(float((d["ratio"] > 2).mean()), 3),
}

fig, ax = plt.subplots(figsize=(3.3, 2.6))
bins = [0, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, d["ratio"].max() + 0.01]
labels = ["<0.8", "0.8-1.0", "1.0-1.2", "1.2-1.5", "1.5-2.0", "2.0-3.0", ">3.0"]
counts = pd.cut(d["ratio"], bins).value_counts().sort_index().values
cols = [MUTED if i < 2 else INK for i in range(len(counts))]
bars = ax.bar(range(len(counts)), counts, color=cols, width=0.82)
for b, c in zip(bars, counts):
    ax.annotate(str(int(c)), xy=(b.get_x() + b.get_width() / 2, c), xytext=(0, 2),
                textcoords="offset points", ha="center", va="bottom", fontsize=6.5,
                color=INK)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_yticks([])
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
ax.set_ylabel("hospitals", labelpad=2)
ax.set_xlabel("post / pre elective volume, 2022 break")
ax.margins(y=0.16)
fig.tight_layout()
fig.savefig(f"{OUT}/fig2_growth_histogram.pdf", bbox_inches="tight")
plt.close(fig)


# ----------------------------------------------------------------------
# FIGURE 3: pre vs post, log-log
# ----------------------------------------------------------------------
LABEL_TOP = 5

GLAB = {"1": "SIH GESTAO 1 (municipal)", "2": "SIH GESTAO 2 (state)"}

fig, ax = plt.subplots(figsize=(4.0, 3.8))
mk = {"1": "o", "2": "s"}
for g, sub in d.groupby("gestao"):
    ax.scatter(sub["pre"], sub["post"], s=18, marker=mk.get(g, "o"),
               facecolors="none" if g == "1" else ACCENT,
               edgecolors=INK if g == "1" else ACCENT, linewidths=0.8,
               alpha=0.85, label=GLAB.get(g, f"SIH GESTAO {g}"))

lo, hi = 4, max(d["pre"].max(), d["post"].max()) * 1.4
ax.plot([lo, hi], [lo, hi], color=MUTED, lw=0.7, ls="--")
ax.plot([lo, hi], [2 * lo, 2 * hi], color=MUTED, lw=0.5, ls=":")
ax.annotate("no change", xy=(lo * 1.15, lo * 1.05), fontsize=6, color=MUTED,
            rotation=45, ha="left", va="top")
ax.annotate("2x", xy=(lo * 1.15, lo * 2.10), fontsize=6, color=MUTED,
            rotation=45, ha="left", va="top")

# top-5 by pre-period volume, plus the largest riser
lab = list(d.nlargest(LABEL_TOP, "pre").index)
# largest riser by ABSOLUTE gain, not by ratio: small denominators dominate ratios
riser = (d["post"] - d["pre"]).nlargest(1).index[0]
if riser not in lab:
    lab.append(riser)

# leader-line placement, alternating side, so adjacent points cannot collide
for k, c in enumerate(sorted(lab, key=lambda c: d.loc[c, "post"])):
    right = k % 2 == 0
    ax.annotate(c, xy=(d.loc[c, "pre"], d.loc[c, "post"]),
                xytext=(16 if right else -16, 10 if right else -12),
                textcoords="offset points", fontsize=5.8, color=INK,
                ha="left" if right else "right", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.4, color=MUTED,
                                shrinkA=0, shrinkB=2))

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(lo, hi)
ax.set_ylim(lo, hi)
ax.set_xlabel("elective cases / month, 2022-01 to 2022-07")
ax.set_ylabel("elective cases / month, 2022-08 to 2023-06")
ax.legend(frameon=False, fontsize=7, loc="upper left")
fig.tight_layout()
fig.savefig(f"{OUT}/fig3_pre_post_scatter.pdf", bbox_inches="tight")
plt.close(fig)


# ----------------------------------------------------------------------
# Group assignment comes from the panel itself now (TP_GESTAO status as of
# 2022-08). The old treat-date decomposition (never/early/late) is removed:
# panel treat dates are systematically late by 1-43 months and the resulting
# +143.9/+39.6 pair is retired. See sections_2_3.tex, "Provider composition
# and the bed-day constraint".
# ----------------------------------------------------------------------
pan["grp"] = pan["group"]
N.pop("table1", None)


# ----------------------------------------------------------------------
# TABLE 2: falsification set
# ----------------------------------------------------------------------
def wmean(sub, var, a, b):
    return sub[sub["COMPETENCIA"].between(a, b)].groupby("COMPETENCIA")[var].sum().mean()


falsi = []

# (i) urgent admissions, statewide
falsi.append(("Urgent surgical admissions, statewide",
              wmean(pan, "urg", *PRE), wmean(pan, "urg", *POST)))

# (ii) urgent, state-administered only
sm = pan[pan["grp"].isin(["always_state", "transferred"])]
falsi.append(("Urgent admissions, state-administered units",
              wmean(sm, "urg", *PRE), wmean(sm, "urg", *POST)))

# (iii) active hospitals
act = pan[pan["elec"] > 0].groupby("COMPETENCIA")["CNES"].nunique()
falsi.append(("Hospitals with $>0$ elective cases",
              act.loc[PRE[0]:PRE[1]].mean(), act.loc[POST[0]:POST[1]].mean()))

# (iv) HHI
def hhi(s):
    p = s / s.sum()
    return (p ** 2).sum() * 1e4


byh = el.groupby(["COMPETENCIA", "CNES"]).size()
h = byh.groupby("COMPETENCIA").apply(hhi)
falsi.append(("Concentration (HHI), elective",
              h.loc[PRE[0]:PRE[1]].mean(), h.loc[POST[0]:POST[1]].mean()))

# (v) entrant contribution to the July-August step
inc = set(pan[pan["COMPETENCIA"].between(*PRE) & (pan["elec"] > 0)]["CNES"])
pan["coh"] = np.where(pan["CNES"].isin(inc), "inc", "ent")
step = (pan[pan["COMPETENCIA"].isin(["2022-07", "2022-08"])]
        .pivot_table(index="coh", columns="COMPETENCIA", values="elec", aggfunc="sum"))
falsi.append(("Elective cases, facilities absent pre-break",
              float(step.loc["ent", "2022-07"]), float(step.loc["ent", "2022-08"])))
N["entrant_share_of_step"] = round(float(
    (step.loc["ent", "2022-08"] - step.loc["ent", "2022-07"]) /
    (step["2022-08"].sum() - step["2022-07"].sum())), 4)

# (vi) GESTAO reclassification at the break (SIH billing field, not CNES TP_GESTAO)
gm = (el[el["COMPETENCIA"].isin(["2022-07", "2022-08"])]
      .groupby(["CNES", "COMPETENCIA"])["GESTAO"]
      .agg(lambda x: x.mode().iat[0]).unstack().dropna())
n_switch = int((gm["2022-07"] != gm["2022-08"]).sum())
falsi.append((f"Facilities changing SIH management code, 2022-07 to 2022-08 (of {len(gm)})",
              float(n_switch), float(n_switch)))

# (vii) submission lag, elective
cir2 = cir.copy()
lag = (pd.PeriodIndex(cir2["COMPETENCIA"], freq="M").asi8
       - pd.PeriodIndex(cir2["adm"], freq="M").asi8)
cir2["lag"] = lag
le = cir2[cir2["CAR_INT"] == "01"]
falsi.append(("Mean submission lag, elective (months)",
              le[le["COMPETENCIA"].between(*PRE)]["lag"].mean(),
              le[le["COMPETENCIA"].between(*POST)]["lag"].mean()))

# (viii) break on admission date instead of processing month
ra = monthly_ratio(cir, index="adm").sort_index()
falsi.append(("Elective/urgent ratio, by admission month",
              ra.loc[PRE[0]:PRE[1], "elec"].sum() / ra.loc[PRE[0]:PRE[1], "urg"].sum(),
              ra.loc[POST[0]:POST[1], "elec"].sum() / ra.loc[POST[0]:POST[1], "urg"].sum()))

t2 = pd.DataFrame(falsi, columns=["quantity", "pre", "post"])
t2["chg"] = (t2["post"] / t2["pre"].replace(0, np.nan) - 1) * 100
N["table2"] = t2.round(3).to_dict("records")

with open(f"{OUT}/tab2_falsification.tex", "w") as f:
    f.write(r"""\begin{tabular}{lrrr}
\toprule
Quantity & Pre & Post & $\Delta\%$ \\
\midrule
""")
    for _, x in t2.iterrows():
        chg = "" if not np.isfinite(x["chg"]) else f"{x['chg']:+.1f}"
        f.write(f"{x['quantity']} & {x['pre']:,.2f} & {x['post']:,.2f} & {chg} \\\\\n")
    f.write(r"""\bottomrule
\end{tabular}
""")


# ----------------------------------------------------------------------
# MERGE, do not replace. scripts/patch_keys.py and patch_model_keys.py write
# keys this script never computes; a bare dump would silently delete them.
# ----------------------------------------------------------------------
NPATH = f"{OUT}/numbers.json"
if os.path.exists(NPATH):
    with open(NPATH) as f:
        prior = json.load(f)
    kept = {k: v for k, v in prior.items() if k not in N}
    N = {**kept, **N}
    print(f"merged {len(kept)} preserved keys: {sorted(kept)}")
with open(NPATH, "w") as f:
    json.dump(N, f, indent=2, default=str)

print(json.dumps(N, indent=2, default=str))
print("\nwrote:", os.listdir(OUT))
