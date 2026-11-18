"""Make measurement plots from the observational results tables."""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def lens_figure(results):
    p=pd.read_csv(results/"lens_budget.csv")
    x=p.eclipse_log_survived_mass_med+p.eclipse_log_survived_mass_upp
    y=p.lg_floor_low
    powerful=p.lg_excess_conservative>.30
    fig,axes=plt.subplots(1,2,figsize=(10,4.05),layout="constrained")
    a,b=axes
    a.scatter(x[~powerful],y[~powerful],s=8,alpha=.28,c="#336e7d",rasterized=True,label="Selected models")
    a.scatter(x[powerful],y[powerful],s=19,c="#b96342",alpha=.85,label="Above +0.30 dex stress test")
    spec=p.specz_agrees
    a.scatter(x[spec],y[spec],s=20,facecolors="none",edgecolors=".2",linewidths=.55,label="DESI-z overlap")
    limits=(9.6,12.8)
    a.plot(limits,limits,color=".6",linewidth=1)
    a.plot(limits,np.array(limits)+.30,color=".5",linewidth=.8,linestyle="--")
    a.set(xlim=limits,ylim=limits,
          xlabel=r"Upper fitted stellar mass, $\log_{10}(M_\star/M_\odot)$",
          ylabel=r"Lensing mass proxy floor, $\log_{10}(M/M_\odot)$")
    a.legend(loc="upper left",frameon=False,fontsize=8)
    edges=np.arange(-1.8,1.45,.08)
    b.hist(p.lg_excess_med,bins=edges,histtype="step",linewidth=1.55,color="#247486",label="Central values")
    b.hist(p.lg_excess_conservative,bins=edges,histtype="step",linewidth=1.55,color="#b96342",
           label="Lower radius/z, upper stars")
    for d in [0.,.30]:
        b.axvline(d,ls="--",lw=.8,color=".45")
    b.set(xlabel=r"$\log_{10}$ (mass proxy floor / fitted stellar mass)",ylabel="Number of systems")
    b.legend(frameon=False,fontsize=8)
    for ax in axes: ax.grid(alpha=.14)
    fig.savefig(results/"Lens_Stellar_Budget.png",dpi=190)
    plt.close(fig)


def bao_figure(results):
    values=json.loads((results/"bao_fits.json").read_text())
    data=pd.DataFrame(values["data"])
    draws=[
        ("curved_lambda","Curved ΛCDM","#247486","o"),
        ("curved_nonaccelerating_lambda","Curved ΛCDM, $q_0\\geq 0$","#a55d36","s"),
        ("matter_and_curvature_only","Matter + curvature only","#78598a","^"),
    ]
    fig, axes=plt.subplots(1,2,figsize=(10,3.85),layout="constrained")
    blocks=(("DV_over_rs","DM_over_rs"),("DH_over_rs",))
    for ax,picks,subtitle in zip(axes,blocks,["Transverse distances, plus low-z $D_V$","Radial distances"],strict=True):
        select=data.observable.isin(picks)
        z=data.z[select]
        ax.axhline(0,color=".45",lw=.8)
        for j,(key,label,color,marker) in enumerate(draws):
            pred=np.asarray(values["full"][key]["prediction"])
            residual=(pred[select]-data.value[select])/data.sigma[select]
            ax.plot(z+(j-1)*.012,residual,marker=marker,lw=1.1,ms=4,c=color,label=label)
        ax.set(title=subtitle,xlabel="Redshift",ylabel="Residual / reported marginal error")
        ax.grid(alpha=.17)
    axes[0].legend(frameon=False,fontsize=8)
    fig.savefig(results/"DESI_BAO_Expansion.png",dpi=190)
    plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("results",type=Path)
    a=p.parse_args()
    lens_figure(a.results)
    bao_figure(a.results)
