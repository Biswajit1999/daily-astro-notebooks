"""Create and execute the authored research notebook without a networked kernel."""
from pathlib import Path
import textwrap

import nbformat as nb
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output


def markdown(s):
    return nb.v4.new_markdown_cell(textwrap.dedent(s).strip())


def code(s):
    return nb.v4.new_code_cell(textwrap.dedent(s).strip())


cells=[
markdown("""
# Projected mass and cosmic acceleration
**Biswajit Jana** · 18 November 2026

**Aim.** Use a projected cluster field to test how the redshift assignment affects lensing mass. Evaluate whether selected Euclid lens models require more projected mass than the fitted stars account for under conservative assumptions. Test present acceleration using independent published DESI distances.
"""),
code("""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

def python(*args):
    return subprocess.run([sys.executable, *map(str,args)], check=True)

if any(importlib.util.find_spec(name) is None for name in ("astropy","scipy","pandas","matplotlib")):
    python("-m","pip","install","-q","astropy>=7.2,<9","numpy>=2","scipy>=1.13","pandas>=2","matplotlib>=3.8")

home=Path("/content") if Path("/content").is_dir() else Path.cwd()
explicit=os.environ.get("DARK_UNIVERSE_ROOT")
slug="euclid-dark-universe"
bundle=home/"Euclid_Dark_Universe_Reproducibility.zip"
relative=Path("euclid-dr1-foundation")/slug
if explicit:
    root=Path(explicit).resolve()
elif (home/"arc_geometry.py").exists():
    root=home
elif (home/slug/"arc_geometry.py").exists():
    root=home/slug
elif bundle.exists():
    with ZipFile(bundle) as archive:
        members=[x for x in archive.namelist() if x.startswith(slug+"/")]
        if any(".." in Path(x).parts or Path(x).is_absolute() for x in members):
            raise ValueError("Unexpected archive path")
        archive.extractall(home,members)
    root=home/slug
else:
    repo=home/"euclid-research"
    if not (repo/".git").exists():
        subprocess.run(["git","clone","--depth","1","--filter=blob:none","--sparse","--branch",
                        "research/euclid-dr1-foundation-day01-20261114",
                        "https://github.com/Biswajit1999/daily-astro-notebooks.git",str(repo)],check=True)
    subprocess.run(["git","-C",str(repo),"sparse-checkout","set",str(relative)],check=True)
    root=repo/relative
sys.path.insert(0,str(root))
inputs=root/"inputs"
results=root/"results"
results.mkdir(exist_ok=True)
import numpy as np
import pandas as pd
from IPython.display import Image, display
"""),
markdown("""
## 1. Archive inventory

The image products are MER mosaics from Euclid DR1-Foundation plus registered DES/DECam bands. The ECLIPSE inputs are the published object and physical-property catalogues. The time-independent model fit uses the released DESI DR2 BAO data vector and covariance.
"""),
code("""
from acquire_public import prepare

provenance=prepare(inputs)
display(pd.DataFrame(provenance)[["filename","bytes","sha256"]])
image_manifest=json.loads((inputs/"arc_image_manifest.json").read_text())
image_bytes=sum(span["end_exclusive"]-span["start"] for band in image_manifest for span in band["ranges"])
print("Checked FITS row bytes for the four image stamps:", image_bytes)
"""),
markdown("""
## 2. The Abell 3128 sightline

Published XMM and Magellan measurements place the background deflector near z = 0.44. The foreground Abell 3128 cluster has z ≈ 0.058. Gemini measured z = 1.4541 for the southwest arc. We use the DES deflector centre and compare the arc ridge across Euclid VIS and ground-based DES rows. This is a targeted remeasurement of a confirmed arc.
"""),
code("""
from arc_geometry import analyse

arc=analyse(inputs,results)
display(Image(filename=str(results/"Abell3128_Observed_Arc.png")))
"""),
code("""
ridges=pd.read_csv(results/"arc_ridges.csv")
display(ridges.pivot(index="pa_deg",columns="band",values="arc_ridge_arcsec").round(2))
display(pd.DataFrame([arc["cluster_redshift_geometry"],arc["foreground_counterfactual"]])
        .assign(geometry=["background cluster","foreground control"]))
print(f'Ratio at fixed angular radius: {arc["mass_ratio_background_to_foreground"]:.2f}')
"""),
markdown("""
We translate the median Euclid arc radius into a one-plane circular Einstein mass proxy. The same angle gives a different enclosed mass when the deflector redshift changes because the angular-diameter distances change. The X-ray and optical redshifts are published evidence. The arc measurement alone spans several position angles, and the proxy leaves line-of-sight structure and the cluster mass profile unresolved.
"""),
markdown("""
## 3. Does the lensing mass exceed the fitted stellar budget?

For a circular lens, the enclosed projected mass scales as $\\theta_E^2 D_l D_s/D_{ls}$. In flat geometry $D_s/D_{ls}>1$. Use unity for the least demanding geometric proxy at a fixed deflector distance and radius. Compare it with the catalogue's fitted total stellar mass, then use a lower radius and photo-z and an upper stellar mass. A further 0.30 dex allowance tests sensitivity to the stellar prior. No joint probability is assigned to these plug-in bounds.
"""),
code("""
from lens_budget import budgets

lenses, budget=budgets(inputs)
lenses.to_csv(results/"lens_budget.csv",index=False)
(results/"lens_budget.json").write_text(json.dumps(budget,indent=2)+"\\n")
display(pd.Series(budget["selection"],name="systems").to_frame())
"""),
code("""
from figures import lens_figure

rows=[
    ("Central values",budget["central_estimate_above_stars"],len(lenses)),
    ("Lower radius and z, upper stellar mass",budget["lower_radius_lower_z_upper_stars"],len(lenses)),
    ("Same bounds with +0.30 dex",budget["lower_radius_lower_z_upper_stars_plus_0p30dex"],len(lenses)),
    ("DESI-z overlap with +0.30 dex",budget["specz_subset_above_stars_plus_0p30dex"],budget["specz_subset"]),
]
display(pd.DataFrame(rows,columns=["assumptions","above budget","total"]))
lens_figure(results)
display(Image(filename=str(results/"Lens_Stellar_Budget.png")))
"""),
markdown("""
The conservative excesses are a candidate list. Gas mass, large-scale structure along the sightline, uncertainties in stellar populations and lens-model geometry remain relevant. The 30-system spectroscopic overlap has a different selection from the full sample. The published candidate catalogue used human grading and multiple selection methods, including machine learning. This notebook uses classical calculations on the released products.
"""),
markdown("""
## 4. DESI BAO and acceleration

Use the observed transverse, radial or volume-averaged distance divided by the sound horizon. For each trial cosmology write the model as a dimensionless distance shape multiplied by the free common factor $c/(H_0 r_d)$. Whiten the observed distances and predictions using the full covariance and solve for this factor by weighted least squares. Compare fits when the present deceleration parameter $q_0$ is unrestricted or constrained to be non-negative.
"""),
code("""
from bao import fit, shape

mean=np.loadtxt(inputs/"bao_mean.txt",dtype=[("z","f8"),("obs","f8"),("tag","U15")])
cov=np.loadtxt(inputs/"bao_cov.txt")
assert len(mean)==13 and cov.shape==(13,13)
assert np.all(np.linalg.eigvalsh(cov)>0)
z=np.array([.2,.6,1.3,2.33])
assert np.allclose(shape(z,np.repeat("DM_over_rs",len(z)),1.,0.),2*(1-1/np.sqrt(1+z)))
assert np.allclose(shape(z,np.repeat("DM_over_rs",len(z)),0.,1.),np.sinh(np.log1p(z)))
display(pd.DataFrame(mean))
"""),
code("""
bao={"full":fit(mean,cov),"without_lyman_alpha":fit(mean,cov,mean["z"]<2),
     "without_lowest_z":fit(mean,cov,mean["z"]>.3),
     "data":[dict(z=float(a["z"]),observable=str(a["tag"]),value=float(a["obs"]),
                  sigma=float(cov[i,i]**.5)) for i,a in enumerate(mean)]}
(results/"bao_fits.json").write_text(json.dumps(bao,indent=2)+"\\n")
display(pd.DataFrame(bao["full"]).T[["omega_m","omega_k","omega_lambda","q0","chi2"]]
        .astype(float).round(4))
"""),
code("""
from figures import bao_figure

bao_figure(results)
display(Image(filename=str(results/"DESI_BAO_Expansion.png")))
for key in ("full","without_lyman_alpha","without_lowest_z"):
    v=bao[key]
    print(f'{key}  chi² curved {v["curved_lambda"]["chi2"]:.2f}  '
          f'curved with q0 >= 0 {v["curved_nonaccelerating_lambda"]["chi2"]:.2f}')
"""),
markdown("""
## 5. Observed RGB composite

NISP H maps to red, VIS to green, and Blanco DECam g to blue. The channels start on the verified common MER grid and are converted to a common AB zero-point scale. Display gains and a shared asinh stretch bring out the arc and central galaxy. Quantitative measurements use the calibrated FITS cutouts. The band-dependent point-spread functions are visible.
"""),
code("""
from rgb_composite import composite

rgb=composite(inputs,results)
display(pd.DataFrame(rgb["channels"]).T)
display(Image(filename=str(results/"Abell3128_RGB.png")))
"""),
markdown("""
## 6. Sensitivity to extraction and cosmological choices

Re-measure the arc over centre offsets, alternative azimuthal backgrounds, smoothing widths, and sector subsets. Each solution uses the same observed images. Recompute the one-plane mass proxy over a limited deflector-redshift grid. Apply a simple uniform sheet and a gas allowance to the catalogue check as illustrative scenarios.

For the BAO fit, profile the present deceleration parameter with curvature free. Omit all distances at one redshift at a time and carry the corresponding covariance block into each refit.
"""),
code("""
from robustness import analyse as stress_tests

stability=stress_tests(inputs,results)
display(pd.DataFrame(stability["arc"]["band_results"]).T)
display(pd.DataFrame([stability["stellar"]]))
display(pd.read_csv(results/"bao_leave_one_redshift.csv").round(4))
display(Image(filename=str(results/"DESI_BAO_Robustness.png")))
"""),
markdown("""
## What we found

- The same southwest arc gives a median ridge radius of **6.06″ in Euclid VIS** and **6.22″ in DECam g**. The circular mass proxy is **9.04 × 10¹² solar masses** for a deflector at z = 0.44. Assigning it to the foreground redshift would reduce that estimate by a factor of **7.88**.
- The catalogue check leaves **26 of 2,161** above the stellar budget after the extra 0.30 dex allowance. **Zero of 30** in the DESI-redshift overlap pass the same allowance. This is an observed-catalogue sensitivity test.
- Curved Lambda-CDM gives **χ² = 9.95** for the DESI distances and **χ² = 173.28** if constrained to present non-acceleration. Removing Lyman-alpha distances gives **9.87 versus 111.00**. The result supports acceleration within these FLRW choices.

The 306 usable VIS extractions span **5.81–6.32″** in median radius. Coupled to a deflector redshift range of 0.42–0.46, they give a one-plane mass sensitivity range of **7.88–10.37 trillion solar masses**. Seven catalogue systems still clear the stellar budget with the +0.30 dex allowance, a uniform external convergence of 0.10 and the illustrative gas allowance. In the curved BAO fit the profile Δχ² = 1 interval is **−0.569 to −0.505**. The seven omitted-redshift fits give **−0.553 to −0.507**.

The observed Euclid cutouts and catalogue support the lensing tests. The acceleration result uses DESI measurements. The sound-horizon scale was profiled in all cases. A measurement of evolving dark energy would require a separate parameter analysis and additional data.
"""),
markdown("""
## Sources and credit

Research author **Biswajit Jana**. Euclid imagery ESA/Euclid/Euclid Consortium/NASA. Independent optical comparison from DES/DECam. Archive access via IRSA.

- [Euclid DR1-Foundation Explanatory Supplement](https://euclid.esac.esa.int/dr/dr1/expsup/)
- [ECLIPSE catalogue and model release](https://doi.org/10.5281/zenodo.19654904)
- [Werner et al. 2007, X-ray morphology of Abell 3128](https://arxiv.org/abs/0708.3253)
- [Nord et al. 2016, spectroscopic confirmation of DES strong lenses](https://arxiv.org/abs/1512.03062)
- [McCleary et al. 2015, weak-lensing mass substructure in Abell 3128](https://arxiv.org/abs/1503.02823)
- [DESI DR2 publications and data](https://data.desi.lbl.gov/doc/papers/dr2/)
"""),
]

notebook=nb.v4.new_notebook(cells=cells,metadata={
    "kernelspec":{"name":"python3","display_name":"Python 3","language":"python"},
    "language_info":{"name":"python"},"authors":[{"name":"Biswajit Jana"}],
    "colab":{"name":"Projected mass and cosmic acceleration — Biswajit Jana","provenance":[]},
})
shell=InteractiveShell.instance()
count=0
for index,cell in enumerate(notebook.cells,1):
    cell.id=f"dark-universe-{index:02}"
    if cell.cell_type!="code":
        continue
    compile(cell.source,cell.id,"exec")
    with capture_output() as output:
        state=shell.run_cell(cell.source,store_history=False)
    if not state.success:
        print(output.stdout)
        print(output.stderr)
        state.raise_error()
    count+=1
    cell.execution_count=count
    for name,value in (("stdout",output.stdout),("stderr",output.stderr)):
        if value:
            cell.outputs.append(nb.v4.new_output("stream",name=name,text=value))
    for item in output.outputs:
        cell.outputs.append(nb.v4.new_output("display_data",data=item.data,metadata=item.metadata))
    print("Executed",cell.id,flush=True)
nb.validate(notebook)
nb.write(notebook,"deliverables/Euclid_Dark_Universe_Colab.ipynb")
print(f"{len(cells)} cells, {count} executed")
