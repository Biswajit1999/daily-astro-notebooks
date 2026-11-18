"""Profile an uncalibrated BAO ruler against simple FLRW expansion histories."""
from pathlib import Path
import argparse
import json

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.linalg import solve_triangular
from scipy.optimize import minimize, minimize_scalar


NODES, WEIGHTS = leggauss(64)


def shape(z, tags, om, ok, w=-1.):
    ode = 1-om-ok
    def e2(x):
        return om*(1+x)**3 + ok*(1+x)**2 + ode*(1+x)**(3*(1+w))
    if np.any(e2(np.linspace(0,z.max(),128))<=0):
        return np.full(z.shape,np.nan)
    h = 1 / np.sqrt(e2(z))
    chi = (z/2)*(1/np.sqrt(e2(z[:,None]*(1+NODES)/2)) @ WEIGHTS)
    if ok > 1e-10:
        m = np.sinh(np.sqrt(ok)*chi)/np.sqrt(ok)
    elif ok < -1e-10:
        m = np.sin(np.sqrt(-ok)*chi)/np.sqrt(-ok)
    else:
        m = chi
    v = np.cbrt(z*h*m*m)
    return np.select([tags=="DM_over_rs", tags=="DH_over_rs", tags=="DV_over_rs"], [m,h,v], default=np.nan)


def fit(mean, cov, mask=None):
    if mask is None:
        mask = np.ones(len(mean),dtype=bool)
    samples = mean[mask]
    z,tags,y = samples["z"],samples["tag"],samples["obs"]
    selected = cov[np.ix_(mask,mask)]
    if not np.allclose(selected, selected.T):
        raise ValueError("Covariance must be symmetric.")
    cov_chol = np.linalg.cholesky(selected)
    whiten = lambda x: solve_triangular(cov_chol,x,lower=True)
    yw=whiten(y)
    def profile(om, ok=0):
        a=shape(z,tags,om,ok)
        w=whiten(a)
        scale=float((w@yw)/(w@w))
        r=yw-scale*w
        return float(r@r), scale, a*scale
    solutions = {}
    specs = {
        "flat_lambda": ((.002,.999),lambda x:0.),
        "flat_nonaccelerating_lambda": ((2/3,1.),lambda x:0.),
        "matter_and_curvature_only": ((0.,2.),lambda x:1-x),
        "einstein_de_sitter": ((1.,1.),lambda x:0.),
    }
    for label,(bounds,ocurv) in specs.items():
        objective=lambda om:profile(om,ocurv(om))[0]
        candidates=list(bounds)
        if bounds[1]>bounds[0]:
            answer=minimize_scalar(objective,bounds=bounds,method="bounded",options={"xatol":1e-12})
            if not answer.success:
                raise RuntimeError(answer.message)
            candidates.append(answer.x)
        om=float(min(candidates,key=objective))
        ok=float(ocurv(om))
        chisq, scale, pred=profile(om,ok)
        solutions[label]=dict(omega_m=om,omega_k=ok,omega_lambda=1-om-ok,
                              q0=1.5*om+ok-1,chi2=chisq,
                              ruler_scale=scale,prediction=pred.tolist(),n=len(z))
    for require_deceleration in (False,True):
        def physics(x):
            om,ok=x
            return np.array([1-om-ok,1.5*om+ok-1]) if require_deceleration else np.array([1-om-ok])

        def curvature_fit(x):
            if not np.isfinite(shape(z,tags,*x)).all():
                return 1e10
            return profile(*x)[0]

        starts=[(.3,0.),(.7,0.),(.4,.6),(.9,-.1),(.9,.06),(1.3,-.5)]
        fits=[minimize(curvature_fit,x,method="SLSQP",bounds=[(.0001,2.0),(-1.2,1.)],
                       constraints=[{"type":"ineq","fun":physics}],options={"ftol":1e-9}) for x in starts]
        eligible=[r for r in fits if r.success and np.min(physics(r.x))>=-1e-8 and r.fun<1e9]
        if not eligible:
            raise RuntimeError("Curved Lambda fit failed.")
        om,ok=map(float,min(eligible,key=lambda r:r.fun).x)
        chisq,scale,pred=profile(om,ok)
        name="curved_nonaccelerating_lambda" if require_deceleration else "curved_lambda"
        solutions[name]=dict(omega_m=om,omega_k=ok,omega_lambda=1-om-ok,
                            q0=1.5*om+ok-1,chi2=chisq,ruler_scale=scale,
                            prediction=pred.tolist(),n=len(z))
    best=solutions["flat_lambda"]
    from scipy.optimize import brentq
    lo,hi = (brentq(lambda x:profile(x)[0]-best["chi2"]-1,*b)
             for b in ((.002,best["omega_m"]),(best["omega_m"],.999)))
    best["omega_m_profile_68"]=[lo,hi]
    best["q0_profile_68"]=[1.5*lo-1,1.5*hi-1]
    return solutions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mean",type=Path); p.add_argument("cov",type=Path); p.add_argument("output",type=Path)
    a=p.parse_args()
    data=np.loadtxt(a.mean,dtype=[("z","f8"),("obs","f8"),("tag","U15")])
    cov=np.loadtxt(a.cov)
    if cov.shape!=(len(data),len(data)) or len(data)!=13:
        raise ValueError("Expected the full 13-point galaxy and Lyman-alpha distance vector.")
    results={"full":fit(data,cov),"without_lyman_alpha":fit(data,cov,data["z"]<2),
             "without_lowest_z":fit(data,cov,data["z"]>.3),
             "data":[dict(z=float(r["z"]),observable=str(r["tag"]),value=float(r["obs"]),sigma=float(cov[i,i]**.5)) for i,r in enumerate(data)]}
    a.output.write_text(json.dumps(results,indent=2)+"\n")
    for dataset,r in results.items():
        if dataset=="data": continue
        print(dataset)
        for label,b in r.items():
            print(label,round(b["omega_m"],5),round(b["q0"],5),round(b["chi2"],3))

if __name__=="__main__":
    main()
