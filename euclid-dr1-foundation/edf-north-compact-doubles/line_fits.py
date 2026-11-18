"""Weighted local continuum and fixed-centre Gaussian line fit."""
import numpy as np


def line_check(w,f,var,valid,center,sigma_A=16.):
    select=valid&(np.abs(w-center)<=120)
    x,y,e=w[select]-center,f[select],np.sqrt(var[select])
    ncore=int((abs(x)<=32).sum()); nside=int((abs(x)>=42).sum())
    out={"center_A":center,"core_bins":ncore,"sideband_bins":nside}
    if ncore<4 or nside<12:
        return {**out,"state":"insufficient_clean_coverage"}
    basis=np.column_stack([np.ones(len(x)),x/120,np.exp(-.5*(x/sigma_A)**2)])
    design=basis/e[:,None]
    beta=np.linalg.lstsq(design,y/e,rcond=None)[0]
    chi=float(np.sum(((y-basis@beta)/e)**2)/(len(x)-3))
    sigma=float(np.sqrt(np.linalg.inv(design.T@design)[2,2]*max(chi,1)))
    return {**out,"state":"measured","snr":float(beta[2]/sigma),"reduced_chi2":chi}
