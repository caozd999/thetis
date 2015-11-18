"""
Tests implicit bottom friction formulation
==========================================

Intended to be executed with pytest.

Tuomas Karna 2015-09-16
"""
from firedrake import *
import numpy as np
import time as timeMod

parameters['coffee'] = {}
exportSolution = False

op2.init(log_level=WARNING)

# set mesh resolution
scale = 1000.0
reso = 2.5*scale
layers = 50
depth = 15.0

# generate unit mesh and transform its coords
x_max = 5.0*scale
x_min = -5.0*scale
Lx = (x_max - x_min)
n_x = int(Lx/reso)
mesh2d = RectangleMesh(n_x, n_x, Lx, Lx, reorder=True)
# move mesh, center to (0,0)
mesh2d.coordinates.dat.data[:, 0] -= Lx/2
mesh2d.coordinates.dat.data[:, 1] -= Lx/2

mesh = ExtrudedMesh(mesh2d, layers=50, layer_height=-depth/layers)

if exportSolution:
    outFile = File('implicit_bf_sol.pvd')

# ----- define function spaces
deg = 1
P1DG = FunctionSpace(mesh, 'DG', degree=1, vfamily='DG', vdegree=1)
P1DGv = VectorFunctionSpace(mesh, 'DG', degree=1, vfamily='DG', vdegree=1)
Uh_elt = FiniteElement('RT', triangle, deg + 1)
Uv_elt = FiniteElement('DG', interval, deg)
U_elt = HDiv(OuterProductElement(Uh_elt, Uv_elt))
# for vertical velocity component
Wh_elt = FiniteElement('DG', triangle, deg)
Wv_elt = FiniteElement('CG', interval, deg + 1)
W_elt = HDiv(OuterProductElement(Wh_elt, Wv_elt))
# in deformed mesh horiz. velocity must actually live in U + W
UW_elt = EnrichedElement(U_elt, W_elt)
# final spaces
V = FunctionSpace(mesh, UW_elt)  # uv

solution = Function(V, name='velocity')
solution_new = Function(V, name='new velocity')
solutionP1DG = Function(P1DGv, name='velocity p1dg')
viscosity_v = Function(P1DG, name='viscosity')
elev_slope = -1.0e-5
source = Constant((-9.81*elev_slope, 0, 0))

z0 = 1.5e-3
kappa = 0.4
drag = (kappa / np.log((depth/layers)/z0))**2
bottom_drag = Constant(drag)
u_bf = 0.035  # NOTE tuned to produce ~correct viscosity profile

viscosity_v.project(Expression('kappa * u_bf * -x[2] * (bath + x[2] + z0) / (bath + z0)',
                    kappa=kappa, u_bf=u_bf, bath=depth, z0=z0))
print 'Cd', drag
print 'u_bf', u_bf
print 'nu', viscosity_v.dat.data.min(), viscosity_v.dat.data.max()

# --- solve mom eq
test = TestFunction(V)
normal = FacetNormal(mesh)


def RHS(solution, sol_old):
    # source term (external pressure gradient
    f = inner(source, test)*dx
    # vertical diffusion (integrated by parts)
    f += -viscosity_v*inner(Dx(solution, 2), Dx(test, 2)) * dx
    # interface term
    diffFlux = viscosity_v*Dx(solution, 2)
    f += (dot(avg(diffFlux), test('+'))*normal[2]('+') +
          dot(avg(diffFlux), test('-'))*normal[2]('-')) * dS_h
    # symmetric interior penalty stabilization
    L = Constant(depth/layers)
    nbNeigh = 2
    o = 1
    d = 3
    sigma = Constant((o + 1)*(o + d)/d * nbNeigh / 2) / L
    gamma = sigma*avg(viscosity_v)
    f += gamma * dot(jump(solution), test('+')*normal[2]('+') + test('-')*normal[2]('-')) * dS_h
    # boundary term
    uv_bot_old = sol_old + Dx(sol_old, 2)*L*0.5
    uv_bot = solution + Dx(solution, 2)*L*0.5  # solver fails
    uv_mag = sqrt(uv_bot_old[0]**2 + uv_bot_old[1]**2) + Constant(1e-12)
    bndFlux = bottom_drag*uv_mag*uv_bot
    ds_bottom = ds_t
    f += dot(bndFlux, test)*normal[2] * ds_bottom

    return f

# ----- define solver

sp = {}
#sp['ksp_type'] = 'cg'
#sp['pc_type'] = 'lu'
#sp['snes_rtol'] = 1.0e-12
#sp['snes_monitor'] = True
##sp['ksp_monitor'] = True
#sp['ksp_monitor_true_residual'] = True
#sp['snes_converged_reason'] = True
#sp['ksp_converged_reason'] = True

dt = 3600.0
timeSteps = 13
dt_const = Constant(dt)

# Backward Euler
F = (inner(solution_new, test)*dx - inner(solution, test)*dx -
     dt_const*RHS(solution_new, solution))
prob = NonlinearVariationalProblem(F, solution_new)
solver = LinearVariationalSolver(prob, solver_parameters=sp)

# ----- solve

if exportSolution:
    outFile << solution
t = 0
for it in range(1, timeSteps + 1):
    t = it*dt
    t0 = timeMod.clock()
    solver.solve()
    solution.assign(solution_new)
    t1 = timeMod.clock()

    if exportSolution:
        outFile << solution
    print '{:4d}  T={:9.1f} s  cpu={:.2f} s'.format(it, it*dt, t1-t0)


def test_solution():
    target_u_min = 0.4
    target_u_max = 1.0
    target_u_tol = 1e-2
    target_zero = 1e-6
    solutionP1DG.project(solution)
    uvw = solutionP1DG.dat.data
    w_max = np.max(np.abs(uvw[:, 2]))
    v_max = np.max(np.abs(uvw[:, 1]))
    print 'w', w_max
    print 'v', v_max
    assert w_max < target_zero, 'z velocity component too large'
    assert v_max < target_zero, 'y velocity component too large'
    u_min = uvw[:, 0].min()
    u_max = uvw[:, 0].max()
    print 'u', u_min, u_max
    assert np.abs(u_min - target_u_min) < target_u_tol, 'minimum u velocity is wrong'
    assert np.abs(u_max - target_u_max) < target_u_tol, 'maximum u velocity is wrong'
    print ' *** PASSED ***'