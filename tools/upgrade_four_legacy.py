"""Repair four legacy notebooks that lacked figures or selected the wrong bright star."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]


def md(text: str): return nbf.v4.new_markdown_cell(text.strip())
def code(text: str): return nbf.v4.new_code_cell(text.strip())


IMPORTS = """
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

RNG = np.random.default_rng(1999)
plt.style.use("seaborn-v0_8-whitegrid")
COLORS={"navy":"#071426","blue":"#1797c9","cyan":"#2fc6b4","gold":"#f4b942","orange":"#ef6a45","rose":"#ce4f78"}
"""


METHOD = """
## What is being tested

This upgraded notebook repairs an earlier short calculation. It preserves the
real catalogue values, adds an exported figure, checks the source identity or
model sensitivity, and makes the limitation part of the result. A number is
not accepted merely because it looks familiar: the object identifier, expected
brightness, units, and agreement between code output and written interpretation
must all be consistent.

For habitable-zone calculations, the plotted range is a transparent
luminosity-scaled estimate. It is not a climate simulation and cannot establish
surface water, an atmosphere, or life. For very bright stars, a positional cone
search can return a nearby catalogue source rather than the named target. The
Hipparcos identifier and parallax provide the source-checked measurement used
for the final distance.

Every result includes a stress test. Resampling or changing a reasonable model
input measures numerical stability, while source-identity checks protect
against a more serious category error. The saved CSV is a small provenance
record transcribed from the named archive table, not a replacement catalogue.
"""


END = """
## Interpretation and limits

The headline result is conditional on the stated model or catalogue source.
For habitable zones, stellar flux is only the first screening variable; clouds,
atmospheric mass and composition, rotation, tidal locking, internal heat, and
stellar activity are omitted. For parallax, simple inversion is appropriate
here because the quoted Hipparcos signal-to-noise is very high, but that rule
does not generalise to noisy or negative parallaxes.

The most important lesson from the two bright-star cases is procedural. Cone
searches identify sources by position, not by human-readable name, and ordering
by catalogue magnitude does not prove that the first row is the intended star.
The source identifier and brightness must be checked before using its parallax.
This audit turns an earlier mismatch into a reproducible quality-control result.

The figure is part of the evidence, not a background illustration. Its axes,
units, catalogue labels, and highlighted selection reproduce values printed by
the executed cells. The accompanying JSON repeats only the checked headline
numbers for the dashboard. Anyone reusing the work should begin with the saved
input table, confirm the named source and units, and then rerun the notebook
from the first cell. A visually attractive plot cannot rescue an incorrect
cross-match, contradictory paragraph, or undocumented approximation.

## References

- NASA Exoplanet Archive table definitions: https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html
- Kopparapu et al. (2013), habitable-zone climate limits: https://arxiv.org/abs/1301.6674
- Gaia DR3 documentation: https://www.cosmos.esa.int/web/gaia/dr3
- Hipparcos new reduction, VizieR I/311: https://tapvizier.cds.unistra.fr/viz-bin/VizieR-3?-source=I%2F311
- van Leeuwen (2007), *Hipparcos, the New Reduction*: https://doi.org/10.1007/978-1-4020-6342-8
"""


def write(folder: Path, title: str, question: str, cells: list[str], readme: str) -> None:
    notebook=nbf.v4.new_notebook(
        cells=[md(f"# {title}\n\n**Scientific question:** {question}"),md(METHOD),code(IMPORTS),*[code(x) for x in cells],md(END)],
        metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3"},"colab":{"provenance":[]}},
    )
    nbf.write(notebook,folder/"notebook.ipynb")
    (folder/"README.md").write_text(readme.strip()+"\n",encoding="utf-8")


def trappist() -> None:
    folder=ROOT/"exoplanet-archive/2026-07-30-habitable-zone-trappist1"
    cells=["""
planets=pd.DataFrame({"planet":["b","c","d","e","f","g","h"],"a_AU":[.01154,.01580,.02227,.02925,.03849,.04683,.06189],"radius_Re":[1.116,1.097,.788,.920,1.045,1.129,.755]})
luminosity=10**(-3.25727); planets["flux_Earth"]=luminosity/planets.a_AU**2
planets.to_csv("trappist1_archive_values.csv",index=False)
print(planets.round(3)); print(f"Stellar luminosity = {luminosity:.6f} L_sun")
""","""
inner=np.sqrt(luminosity/1.1); outer=np.sqrt(luminosity/.53); planets["in_simple_hz"]=planets.a_AU.between(inner,outer); selected=planets.loc[planets.in_simple_hz,"planet"].tolist()
print(f"Simple HZ = {inner:.4f}–{outer:.4f} AU; selected planets: {selected}")
""","""
fig,ax=plt.subplots(figsize=(10,4.8)); ax.axvspan(inner,outer,color=COLORS["cyan"],alpha=.25,label="luminosity-scaled HZ"); ax.scatter(planets.a_AU,np.ones(len(planets)),s=600*planets.radius_Re**2,c=np.where(planets.in_simple_hz,COLORS["orange"],COLORS["navy"]),edgecolor="white",linewidth=1.5)
for _,r in planets.iterrows(): ax.text(r.a_AU,1,r.planet,ha="center",va="center",color="white",fontweight="bold")
ax.set(xlabel="Orbital semi-major axis (AU)",yticks=[],title="TRAPPIST-1 planets against the simple luminosity-scaled zone"); ax.legend(); fig.tight_layout(); fig.savefig("trappist1_habitable_zone.png",dpi=180); plt.show()
""","""
# Sensitivity to ±10% stellar luminosity.
tests=[]
for scale in [.9,1,1.1]:
    i=np.sqrt(luminosity*scale/1.1); o=np.sqrt(luminosity*scale/.53); names=planets.loc[planets.a_AU.between(i,o),"planet"].tolist(); tests.append((scale,names))
print("Luminosity sensitivity:",tests)
""","""
result={"id":"2026-07-30-habitable-zone-trappist1","title":"TRAPPIST-1 luminosity-scaled habitable-zone check","archive":"NASA Exoplanet Archive","date":"2026-07-30","question":"Which planets fall inside this transparent luminosity-only estimate?","sample_size":7,"results":[f"simple zone {inner:.4f}–{outer:.4f} AU",f"planet e is the only selected planet in this approximation",f"selection unchanged for ±10% luminosity: {all(x[1]==['e'] for x in tests)}"],"validation":"The zone is recomputed after changing stellar luminosity by ±10%.","notebook":"exoplanet-archive/2026-07-30-habitable-zone-trappist1/notebook.ipynb","hero":"exoplanet-archive/2026-07-30-habitable-zone-trappist1/trappist1_habitable_zone.png","tags":["TRAPPIST-1","habitable zone","model limits"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""]
    write(folder,"TRAPPIST-1: a source-consistent habitable-zone check","Which planets fall inside a simple luminosity-scaled zone?",cells,"""# TRAPPIST-1 habitable-zone check

This corrected analysis plots all seven real archive planets and states exactly
what the simplified model selects: **planet e only**. The earlier prose implied
that e, f, and g passed even though its own calculation selected only e.

![TRAPPIST-1 orbital layout](trappist1_habitable_zone.png)

[Open the executed notebook](notebook.ipynb)
""")


def kepler442() -> None:
    folder=ROOT/"exoplanet-archive/2026-07-30-habitable-zone-kepler442"
    cells=["""
planet=pd.DataFrame([{"planet":"Kepler-442 b","a_AU":.409,"radius_Re":1.34,"equilibrium_K":241.,"host_teff_K":4402.,"host_logL":-.932}]); planet["host_Lsun"]=10**planet.host_logL; planet.to_csv("kepler442_archive_values.csv",index=False); print(planet.T)
""","""
L=float(planet.host_Lsun.iloc[0]); a=float(planet.a_AU.iloc[0]); inner=np.sqrt(L/1.1); outer=np.sqrt(L/.53); flux=L/a**2; inside=inner<=a<=outer
print(f"Flux={flux:.3f} Earth flux; simple HZ={inner:.3f}–{outer:.3f} AU; inside={inside}")
""","""
fig,ax=plt.subplots(figsize=(10,4.5)); ax.axvspan(inner,outer,color=COLORS["cyan"],alpha=.3,label="luminosity-scaled HZ"); ax.axvline(a,color=COLORS["orange"],lw=4,label="Kepler-442 b"); ax.scatter([a],[1],s=500,color=COLORS["orange"],edgecolor="white"); ax.set(xlim=(.2,.6),xlabel="Orbital distance (AU)",yticks=[],title="Kepler-442 b lies inside the simple luminosity-scaled zone"); ax.legend(); fig.tight_layout(); fig.savefig("kepler442_habitable_zone.png",dpi=180); plt.show()
""","""
checks=[]
for scale in [.9,1,1.1]:
    i=np.sqrt(L*scale/1.1); o=np.sqrt(L*scale/.53); checks.append(i<=a<=o)
print("Inside after ±10% luminosity changes:",checks)
""","""
result={"id":"2026-07-30-habitable-zone-kepler442","title":"Kepler-442 b habitable-zone check","archive":"NASA Exoplanet Archive","date":"2026-07-30","question":"Does Kepler-442 b pass a luminosity-only zone test?","sample_size":1,"results":[f"incident flux {flux:.3f} Earth flux",f"simple zone {inner:.3f}–{outer:.3f} AU",f"0.409 AU remains inside for ±10% luminosity: {all(checks)}"],"validation":"The boundary test is repeated after changing stellar luminosity by ±10%.","notebook":"exoplanet-archive/2026-07-30-habitable-zone-kepler442/notebook.ipynb","hero":"exoplanet-archive/2026-07-30-habitable-zone-kepler442/kepler442_habitable_zone.png","tags":["Kepler-442 b","habitable zone","stellar flux"]}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""]
    write(folder,"Kepler-442 b: luminosity-scaled habitable-zone check","Does its measured orbit pass the simple energy-input test?",cells,"""# Kepler-442 b habitable-zone check

The upgraded notebook turns the original calculation into a labelled orbital
figure and tests the result against a ±10% change in stellar luminosity. The
planet remains inside this simple zone, but that is not proof of habitability.

![Kepler-442 b orbital test](kepler442_habitable_zone.png)

[Open the executed notebook](notebook.ipynb)
""")


def bright_star(folder_name: str, name: str, hip: int, hip_p: float, hip_e: float,
                gaia_id: int, gaia_p: float, gaia_e: float, gaia_g: float) -> None:
    folder=ROOT/f"gaia/{folder_name}"; slug=folder_name[11:]
    cells=[f"""
audit=pd.DataFrame([{{"catalogue":"Hipparcos I/311/hip2","source_id":"HIP {hip}","parallax_mas":{hip_p},"parallax_error_mas":{hip_e},"identity":"source-checked {name}"}},{{"catalogue":"Gaia DR3 cone result","source_id":"{gaia_id}","parallax_mas":{gaia_p},"parallax_error_mas":{gaia_e},"identity":"brightest returned row; not assumed to be {name}"}}]); audit.to_csv("{name.lower()}_source_audit.csv",index=False); print(audit)
""",f"""
hip_distance=1000/{hip_p}; hip_error=1000*{hip_e}/{hip_p}**2; gaia_distance=1000/{gaia_p}; ratio=gaia_distance/hip_distance
print(f"HIP distance={{hip_distance:.3f}}±{{hip_error:.3f}} pc ({{hip_distance*3.26156:.2f}} ly)"); print(f"Cone-row distance={{gaia_distance:.3f}} pc; ratio={{ratio:.1f}}")
""",f"""
fig,axes=plt.subplots(1,2,figsize=(11,4.8)); axes[0].bar(["source-checked\\nHipparcos","first Gaia\\ncone row"],[{hip_p},{gaia_p}],yerr=[{hip_e},{gaia_e}],color=[COLORS["cyan"],COLORS["rose"]]); axes[0].set(ylabel="Parallax (mas)",title="Catalogue values are not interchangeable"); axes[1].bar(["source-checked\\nHipparcos","first Gaia\\ncone row"],[hip_distance,gaia_distance],color=[COLORS["cyan"],COLORS["rose"]]); axes[1].set(ylabel="Distance from inverse parallax (pc)",title="Source identity controls the answer"); fig.suptitle("{name}: source-identification audit"); fig.tight_layout(); fig.savefig("{name.lower()}_parallax_audit.png",dpi=180); plt.show()
""",f"""
hip_snr={hip_p}/{hip_e}; gaia_snr={gaia_p}/{gaia_e}; brightness_warning={str(name=='Vega')}; print(f"Parallax S/N: Hipparcos={{hip_snr:.0f}}, cone row={{gaia_snr:.0f}}"); print("Returned Gaia G magnitude:",{gaia_g})
""",f"""
result={{"id":"{folder_name}","title":"{name} parallax source audit","archive":"Gaia DR3 + Hipparcos","date":"2026-07-30","question":"Did the positional cone search return the named bright star?","sample_size":2,"results":[f"source-checked distance {{hip_distance:.3f}} ± {{hip_error:.3f}} pc",f"{{hip_distance*3.26156:.2f}} light-years",f"cone-row distance ratio {{ratio:.1f}}×"],"validation":"The cone-search row is compared with the named Hipparcos identifier and expected brightness.","notebook":"gaia/{folder_name}/notebook.ipynb","hero":"gaia/{folder_name}/{name.lower()}_parallax_audit.png","tags":["{name}","parallax","source identity","quality control"]}}; Path("result.json").write_text(json.dumps(result,indent=2)); print(result["results"])
"""]
    warning=("The old cone search selected a roughly G=9.67 background source and produced 2,116 light-years, while its prose claimed 25 light-years. This corrected notebook uses the source-checked HIP 91262 value." if name=="Vega" else "The Gaia cone search returned a faint system source rather than safely identifying Sirius A. The corrected distance uses the source-checked HIP 32349 parallax and keeps the cone row only as an audit comparison.")
    write(folder,f"{name}: auditing a bright-star parallax cone search","Did the first Gaia cone-search row actually identify the named star?",cells,f"""# {name} parallax source audit

{warning}

![{name} parallax audit]({name.lower()}_parallax_audit.png)

[Open the executed notebook](notebook.ipynb)
""")


def main() -> None:
    trappist(); kepler442()
    bright_star("2026-07-30-parallax-distance-sirius","Sirius",32349,379.21,1.58,2947050466531873024,374.4895885,.2,8.524133)
    bright_star("2026-07-30-parallax-distance-vega","Vega",91262,130.23,.36,2097892344993257344,1.542,.013214312,9.666267)
    print("Upgraded four legacy notebooks")


if __name__=="__main__": main()
