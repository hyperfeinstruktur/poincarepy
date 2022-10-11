import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import argparse
import solver
import pickle as pkl
from common import PoincareCollection, Tomography
from potentials import *
import scipy.optimize as scpopt

parser = argparse.ArgumentParser(
    description="Poincare x vx Section of Logarithmic potential"
)
# Integration Parameters (Collection parameters)
parser.add_argument("-tf",type=float,default=100,help="Maximal integration time. If --no_count, this will be the obligatory final time")
parser.add_argument("-nb_crossings",type=int,default= 40,help="Terminate integration after n crossings of the plane (=nb of points in the Poincaré map)")
parser.add_argument("-nb_orbs",type=int,default=11,help="Number of orbits to sample if --fill is passed")
parser.add_argument("--no_count",action='store_true',help="Integrate until t=tf, without counting the crossings")

# Logarithmic Potential Parameters
parser.add_argument("-v0",type=float,default=10.,help="Characteristic Velocity")
parser.add_argument("-rc",type=float,default=1.,help="Characteristic Radius")
parser.add_argument("-q",type=float,default=0.8,help="Flattening Parameter")

# Tomography Parameters
parser.add_argument("-Emin",type=float,default=30.)
parser.add_argument("-Emax",type=float,default=200.)
parser.add_argument("-nb_E",type=int,default=3,help="Number of energy slices in tomographic mode")
parser.add_argument("--no_orbit_redraw",action='store_false')

# Script Parameters
parser.add_argument("--progress",action='store_true',help="Use tqdm to show progress bar")
parser.add_argument("--save",action='store_true')
parser.add_argument("-open",type=str,default=None)


args = parser.parse_args()

"""
Reorganized version of logpoincare for tomographic plots.
Objective: separate data generation and visualisation to be able to export data

"""

# Integration Parameters
t_span = (0,args.tf)
nb_points_orbit = 20000
t_eval = np.linspace(0,args.tf,nb_points_orbit) # ts at which the output of the integrator is stored.
                                           # in reality, integration normally stops before tf
                                           # (if a the given number of crossings is reached)
                                           # and so a large part of these ts will not be used.

# Decide whether to terminate integration after N crossings or integrate until tf
if args.no_count:
    event_count_max = None
else:
    event_count_max = args.nb_crossings

# Event function (y plane crossing)
def event_yplanecross(t,y):
    return y[1]
event_yplanecross.direction = 1

# Progress bar:
if args.progress:
    from tqdm import tqdm
    progbar = lambda itb: tqdm(itb)
else:
    progbar = lambda itb: itb

# This function is a draft
def integrate_energy(pot,E,N_orbits,t_span,t_eval,event,event_count_max,xlim=None):
    g = lambda x: E-pot.phi(np.array([x,np.zeros_like(x)]))
    gprime = lambda x: pot.accel(np.array([x,np.zeros_like(x),np.zeros_like(x),np.zeros_like(x)]))[0]
    xlim = 0.999*scpopt.newton(g,(-1,1),gprime)
    if max(xlim) > 1e5: raise ValueError("Probable error in xlim computation for E={:1f}".format(E))
    print(E)
    print(xlim)
    print(g(xlim))
    print()
    x_ic = np.linspace(xlim[0],xlim[1],N_orbits)
    ydot_ic = np.sqrt(2*(E-pot.phi([x_ic,np.zeros(N_orbits)])))
    #print(pot.phi(np.array([1,0,0,0])))
    f = lambda t,y: pot.RHS(t,y)
    orbits = []
    sections = []
    for k in range(N_orbits):
        y0 = [x_ic[k],0,0,ydot_ic[k]]
        res = solver.integrate_orbit(f,t_span,y0,t_eval=t_eval,events=event,event_count_end=event_count_max)
        orbits.append(res['y'][0:2])
        sections.append(res['y_events'][0][:,[0,2]].T)
    return orbits,sections


if __name__ == "__main__":
    # If no previous file is loaded, create new collection by
    # integrating nb_orbs at each energy level
    if args.open is None:
        # Construct a potential here
        """
        pot = LogarithmicPotential(args.v0,args.rc,args.q,zeropos=(2,2))
        """
        r0 = (0,0)
        logpot = LogarithmicPotential(zeropos=r0)
        rotpot = zRotation(0.3,zeropos=r0)

        pot = CombinedPotential(logpot,rotpot)
        #pot = HomospherePotential(a=5.0,M=1000.,zeropos=r0)

        # Test if energy range is compatible with potential
        E_range = np.linspace(args.Emin,args.Emax,args.nb_E)
        potrange = pot.get_energyrange()
        if np.any(np.logical_or(np.less(E_range,potrange[0]),np.greater(E_range,potrange[1]))):
            raise ValueError(
            "Some of the given energies are outside the scope of the provided potential ({:.1f},{:.1f})"
            .format(potrange[0],potrange[1])
            )
        orbslist = []
        secslist = []
        for e in progbar(E_range):
            o,s = integrate_energy(pot,e,args.nb_orbs,t_span,
                t_eval,event_yplanecross,event_count_max,xlim=None)
            orbslist.append(o)
            secslist.append(s)
        
        col = PoincareCollection(E_range,orbslist,secslist,pot.info())
    else:
        with open(args.open,'rb') as f:
            col = pkl.load(f)

    fs = (15,7)
    fig, ax = plt.subplots(1,2,figsize=fs)
    tom = Tomography(ax[0],ax[1],col,args.no_orbit_redraw)

    if args.save:
        with open('PoincareCollection.pkl','wb') as f:
            pkl.dump(col,f)
    plt.show()