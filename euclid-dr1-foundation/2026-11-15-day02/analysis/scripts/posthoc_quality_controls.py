"""Day 02 post-hoc, independently specified classical-statistics stress test.
Uses only real public Euclid DR1-Foundation data already extracted and committed.
These analyses were specified after the initial results and are not confirmatory.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"observed_results"
OUT=DATA/"posthoc"
OUT.mkdir(parents=True,exist_ok=True)
clean=pd.read_csv(DATA/"strict_clean.csv")
allmatched=pd.read_csv(DATA/"all_morphology_matched.csv.gz")
assert len(clean)==782 and len(allmatched)==1576
assert clean.object_id.is_unique and allmatched.object_id.is_unique
for t in [clean,allmatched]:
 t["log_ha"]=np.log10(t.ha_flux)
 t["log_vis"]=np.log10(t.flux_vis_2fwhm_aper)
 t["log_kron"]=np.log10(t.kron_radius)

model="log_kron ~ log_ha + log_vis + spe_z + C(tileid)"
fit=smf.ols(model,clean).fit(cov_type="HC3")
lo,hi=fit.conf_int().loc["log_ha"].tolist()
result={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"data_release":"Euclid DR1-Foundation",
        "analysis_type":"post-hoc, exploratory; separate from preregistered Day 02 median-strata test",
        "quality":{"n_clean":len(clean),"n_matched":len(allmatched),
          "clean_fraction":float(len(clean)/len(allmatched)),
          "clean_median_kron_pix":float(clean.kron_radius.median()),
          "flagged_median_kron_pix":float(allmatched.loc[~allmatched.clean,"kron_radius"].median()),
          "clean_median_ha_flux":float(clean.ha_flux.median()),
          "flagged_median_ha_flux":float(allmatched.loc[~allmatched.clean,"ha_flux"].median()),
          "clean_objects_multifit_spread_gt_20_percent":int((clean.flux_range_over_median>.2).sum())},
        "hc3_regression":{"formula":model,"n":len(clean),
          "ha_slope_dex_per_dex":float(fit.params["log_ha"]),
          "ha_standard_error_hc3":float(fit.bse["log_ha"]),
          "ha_ci95":[float(lo),float(hi)],"ha_nominal_p":float(fit.pvalues["log_ha"]),
          "vis_slope":float(fit.params["log_vis"]),
          "vis_nominal_p":float(fit.pvalues["log_vis"]),
          "r_squared":float(fit.rsquared)}}
# Post-hoc partial rank residual correlation. Nominal p is not a calibrated partial-correlation significance test.
for c in ["log_ha","log_kron","log_vis","spe_z"]: clean[c+"_rank"]=clean[c].rank()
x=smf.ols("log_ha_rank ~ log_vis_rank + spe_z_rank + C(tileid)",clean).fit().resid
y=smf.ols("log_kron_rank ~ log_vis_rank + spe_z_rank + C(tileid)",clean).fit().resid
rho=spearmanr(x,y)
result["residual_rank_correlation"]={"rho":float(rho.statistic),"nominal_p":float(rho.pvalue),
        "note":"post-hoc approximated partial rank association; not a preregistered independent discovery test"}
# Sensitivity to repeated line-fit discordance, not retroactive selection of a primary sample.
stable=clean[clean.flux_range_over_median<=.2]
rob=smf.ols(model,stable).fit(cov_type="HC3")
a,b=rob.conf_int().loc["log_ha"].tolist()
result["limited_multifit_disagreement"]={"max_relative_range":.2,"n":len(stable),
        "ha_slope":float(rob.params["log_ha"]),"ha_ci95":[float(a),float(b)],
        "ha_nominal_p":float(rob.pvalues["log_ha"])}
# Tile-stratified observed quality attrition. This plot uses actual source counts.
ct=allmatched.groupby(["tileid","clean"]).size().unstack(fill_value=0).sort_index()
fig,ax=plt.subplots(figsize=(8.5,4.7))
xx=np.arange(len(ct))
ax.bar(xx,ct[True].to_numpy(),label="Strict clean",color="tab:blue")
ax.bar(xx,ct[False].to_numpy(),bottom=ct[True].to_numpy(),label="Excluded by quality flags",color="tab:orange")
ax.set_xticks(xx,[str(t) for t in ct.index],rotation=30,ha="right")
ax.set(xlabel="Euclid MER tile ID",ylabel="Matched source count",
       title="Observed DR1-Foundation Hα sample: quality selection by tile")
ax.legend(fontsize=9);fig.tight_layout()
fig.savefig(OUT/"tile_quality_attrition.png",dpi=190);plt.close(fig)
(OUT/"posthoc_metrics.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
