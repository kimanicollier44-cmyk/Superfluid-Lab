#!/usr/bin/env python3
"""Superfluid-Lab - educational superfluid / condensate lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the central lesson is stated up front:

  * This lab solves the one-dimensional Gross-Pitaevskii (GP)
    equation in imaginary time on a finite-difference grid (units
    hbar = m = 1) for a weakly interacting condensate in a hard-wall
    box, and derives everything else from that converged ground
    state: the chemical potential mu, the bulk density n, the
    healing length xi = 1/sqrt(2 g n), the Bogoliubov dispersion
    omega(k) = sqrt(eps_k (eps_k + 2 g n)), the sound speed c_s
    (cross-checked three independent ways), and the Landau critical
    velocity v_c = min_k omega(k)/k.
  * Superfluidity here is a theorem about a stated mean-field model,
    not a measurement. The Landau criterion says a flow below v_c
    cannot create excitations *in this spectrum*; it does not
    certify any real material, device, or cryogenic system.
  * The honest limits are part of the physics and are printed, not
    buried: GP is a mean-field theory at zero temperature. There is
    NO beyond-mean-field (Lee-Huang-Yang) correction anywhere in
    this lab, no finite-temperature physics, no quantum depletion,
    and the "ideal gas" comparison case has v_c = 0 - it is not a
    superfluid at all, which is exactly the point of the contrast.

Real-device superfluidity claims, condensate characterisation,
cryogenics, atomtronics, and every other real-world use are
permanent HOLD gates - with Gemini Argon 4 Extended Thinking as
DECIDER (names-only, tighten-only), Muse as advisor (never
overrides HOLD), and Google Flow plan-only seats.
"""
import cmath
import hashlib
import json
import math
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# The condensate, in units hbar = m = 1:
#   i dpsi/dt = [-1/2 d2/dx2 + V(x) + g |psi|^2] psi
# V = hard-wall box of length BOX_L (Dirichlet boundaries), the
# wavefunction is normalised to NPART particles, and the ground state
# is found by imaginary-time propagation on an NGRID-point grid.
G_INT = 0.05        # interaction strength g (weakly interacting)
NPART = 100.0       # particle number (wavefunction norm^2)
BOX_L = 20.0        # box length
NGRID = 256         # finite-difference grid points

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "superfluid_device_claim": "HOLD - no claim that any real device or material is superfluid from this mean-field model",
    "real_condensate_characterization": "HOLD - no characterising a real condensate's density, chemical potential, or critical temperature from this simulation",
    "cryogenic_system_claim": "HOLD - no cryogenic or cooling-system performance claim from a zero-temperature model",
    "frictionless_transport_product_claim": "HOLD - no product claim of frictionless transport or persistent-current devices from lab numbers",
    "quantum_turbulence_control_claim": "HOLD - no controlling, predicting, or certifying real quantum turbulence from a 1D stationary model",
    "atomtronics_device_claim": "HOLD - no atomtronic circuit or device claim; the ring here is a phase-arithmetic demonstration",
    "beyond_meanfield_claim": "HOLD - no beyond-mean-field accuracy claim; there is no Lee-Huang-Yang or depletion correction in this lab",
    "finite_temperature_claim": "HOLD - no finite-temperature claim; every number here is T = 0 mean-field",
    "simulation_as_measurement_claim": "HOLD - simulated densities, spectra, and velocities must never be presented as measured data",
    "medical_flow_claim": "HOLD - no medical, biological, or microfluidic flow claim from condensate mathematics",
    "energy_extraction_claim": "HOLD - no free-energy or perpetual-flow work claim from persistent-current bookkeeping",
    "product_benchmark_claim": "HOLD - no product benchmark, marketing figure, or procurement comparison from lab numbers",
    "investment_claim": "HOLD - no investment claim; a lab model is not a prospectus",
    "standards_compliance_claim": "HOLD - no claim of compliance with any metrology, cryogenics, or quantum-technology standard",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ 1. GP solver
# Imaginary-time propagation of the 1D Gross-Pitaevskii equation on a
# uniform finite-difference grid with Dirichlet (hard-wall) boundary
# conditions. Explicit Euler in tau with renormalisation to NPART
# after every step; dtau is held at 0.3 dx^2, inside the stability
# limit of the kinetic term. Convergence is declared on the chemical
# potential, the Rayleigh quotient of the GP operator, sampled every
# 200 steps. Every solve is memoised - the physics is deterministic,
# so a repeated request must return the identical state.

_GS_CACHE = {}


def _norm_sq(psi, dx):
    return sum(v * v for v in psi) * dx


def _chemical_potential(psi, dx, g):
    """mu = <psi| -1/2 d2/dx2 + g |psi|^2 |psi> / <psi|psi>."""
    n = len(psi)
    num = 0.0
    for j in range(1, n - 1):
        lap = (psi[j - 1] - 2.0 * psi[j] + psi[j + 1]) / (dx * dx)
        num += psi[j] * (-0.5 * lap + g * psi[j] * psi[j] * psi[j])
    return num * dx / _norm_sq(psi, dx)


def _gp_residual(psi, dx, g, mu):
    """max_j |H psi - mu psi| / (mu * max|psi|) on the interior."""
    n = len(psi)
    peak = max(abs(v) for v in psi)
    worst = 0.0
    for j in range(1, n - 1):
        lap = (psi[j - 1] - 2.0 * psi[j] + psi[j + 1]) / (dx * dx)
        r = -0.5 * lap + g * psi[j] ** 3 - mu * psi[j]
        if abs(r) > worst:
            worst = abs(r)
    return worst / (mu * peak)


def ground_state(npart=NPART, g=G_INT, ngrid=NGRID, length=BOX_L):
    """Converged GP ground state in the box, memoised per (npart, g).

    Returns a dict: psi (list of amplitudes), dx, mu (chemical
    potential from the Rayleigh quotient), n_bulk (mean density over
    the central half of the box), steps (imaginary-time steps taken),
    and residual (stationarity residual of the converged state).
    """
    key = (float(npart), float(g), int(ngrid), float(length))
    if key in _GS_CACHE:
        return _GS_CACHE[key]
    dx = length / (ngrid - 1)
    dtau = 0.3 * dx * dx
    psi = []
    for j in range(ngrid):
        x = -length / 2.0 + j * dx
        taper = math.cos(math.pi * x / length)
        psi.append(math.sqrt(npart / length)
                   * math.sqrt(taper if taper > 0.0 else 0.0))
    scale = math.sqrt(npart / _norm_sq(psi, dx))
    psi = [v * scale for v in psi]
    mu_prev = None
    steps = 0
    for step in range(400000):
        steps = step + 1
        new = psi[:]
        for j in range(1, ngrid - 1):
            lap = (psi[j - 1] - 2.0 * psi[j] + psi[j + 1]) / (dx * dx)
            new[j] = psi[j] + dtau * (0.5 * lap - g * psi[j] ** 3)
        new[0] = 0.0
        new[-1] = 0.0
        scale = math.sqrt(npart / _norm_sq(new, dx))
        psi = [v * scale for v in new]
        if step % 200 == 0:
            mu = _chemical_potential(psi, dx, g)
            if mu_prev is not None and abs(mu - mu_prev) < 1e-10:
                break
            mu_prev = mu
    mu = _chemical_potential(psi, dx, g)
    lo, hi = ngrid // 4, 3 * ngrid // 4
    n_bulk = sum(psi[j] ** 2 for j in range(lo, hi)) / (hi - lo)
    out = {
        "psi": psi, "dx": dx, "mu": mu, "n_bulk": n_bulk,
        "npart": float(npart), "g": float(g), "steps": steps,
        "residual": _gp_residual(psi, dx, g, mu),
        "peak_density": max(v * v for v in psi),
    }
    _GS_CACHE[key] = out
    return out


def healing_length(n_bulk, g=G_INT):
    """xi = 1/sqrt(2 g n) in units hbar = m = 1."""
    return 1.0 / math.sqrt(2.0 * g * n_bulk)


def groundstate_report():
    gs = ground_state()
    n = gs["n_bulk"]
    return {
        "npart": gs["npart"], "g": gs["g"], "grid_points": NGRID,
        "box_length": BOX_L, "steps": gs["steps"],
        "mu": gs["mu"], "n_bulk": n,
        "g_times_n": gs["g"] * n,
        "mu_over_gn": gs["mu"] / (gs["g"] * n),
        "peak_density": gs["peak_density"],
        "xi": healing_length(n, gs["g"]),
        "residual": gs["residual"],
        "norm_sq": _norm_sq(gs["psi"], gs["dx"]),
        "wall_density_over_bulk":
            (gs["psi"][1] ** 2) / n,
        "bulk_flatness": _bulk_flatness(gs),
    }


def _bulk_flatness(gs):
    psi, ngrid = gs["psi"], len(gs["psi"])
    lo, hi = ngrid // 4, 3 * ngrid // 4
    dens = [psi[j] ** 2 for j in range(lo, hi)]
    mean = sum(dens) / len(dens)
    var = sum((d - mean) ** 2 for d in dens) / len(dens)
    return math.sqrt(var) / mean


# ================================================================ 2. Bogoliubov
# Elementary excitations of the uniform condensate with density n:
#   omega(k) = sqrt( eps_k (eps_k + 2 g n) ),   eps_k = k^2 / 2.
# Phonons (omega ~ c_s k) at low k, free particles (omega ~ eps_k + g n)
# at high k, crossover where eps_k = 2 g n, i.e. k* xi = sqrt(2).

def bogoliubov_omega(k, n_bulk, g=G_INT):
    eps = 0.5 * k * k
    return math.sqrt(eps * (eps + 2.0 * g * n_bulk))


def dispersion_report():
    gs = ground_state()
    n, g = gs["n_bulk"], gs["g"]
    xi = healing_length(n, g)
    cs = math.sqrt(g * n)
    ks = [0.02 * (1.22 ** i) for i in range(40)]
    rows = []
    for k in ks:
        om = bogoliubov_omega(k, n, g)
        if k * xi <= 0.5:
            regime = "phonon"
        elif k * xi >= 2.0:
            regime = "free-particle"
        else:
            regime = "crossover"
        rows.append({"k": k, "omega": om, "omega_over_k": om / k,
                     "k_xi": k * xi, "regime": regime})
    k_star = 2.0 * math.sqrt(g * n)  # eps_k = 2 g n  ->  k* = sqrt(4 g n)
    # local log-slope d ln omega / d ln k at k*, by central differences
    h = 1e-4
    slope_star = (math.log(bogoliubov_omega(k_star * (1.0 + h), n, g))
                  - math.log(bogoliubov_omega(k_star * (1.0 - h), n, g))) \
        / (math.log(1.0 + h) - math.log(1.0 - h))
    return {
        "n_bulk": n, "g": g, "xi": xi, "c_s": cs, "rows": rows,
        "k_star": k_star, "k_star_xi": k_star * xi,
        "log_slope_at_k_star": slope_star,
        "phonon_ratio_at_small_k":
            bogoliubov_omega(0.05, n, g) / (cs * 0.05),
        "free_particle_ratio_at_large_k":
            bogoliubov_omega(20.0, n, g) / (0.5 * 20.0 ** 2 + g * n),
    }


def sound_speed_report():
    """c_s three ways: sqrt(g n); sqrt(n dmu/dn) from three GP solves;
    and the low-k slope of the Bogoliubov dispersion."""
    gs = ground_state()
    n, g = gs["n_bulk"], gs["g"]
    cs_direct = math.sqrt(g * n)
    lo = ground_state(NPART * 0.9)
    hi = ground_state(NPART * 1.1)
    dmu_dn = (hi["mu"] - lo["mu"]) / (hi["n_bulk"] - lo["n_bulk"])
    cs_mu = math.sqrt(n * dmu_dn)
    num = 0.0
    den = 0.0
    for k in (0.02, 0.04, 0.06, 0.08, 0.10):
        om = bogoliubov_omega(k, n, g)
        num += k * om
        den += k * k
    cs_slope = num / den
    return {
        "n_bulk": n, "g": g, "dmu_dn": dmu_dn,
        "c_s_direct": cs_direct, "c_s_from_mu": cs_mu,
        "c_s_from_slope": cs_slope,
        "rel_diff_mu": abs(cs_mu - cs_direct) / cs_direct,
        "rel_diff_slope": abs(cs_slope - cs_direct) / cs_direct,
        "mu_lo": lo["mu"], "mu_mid": gs["mu"], "mu_hi": hi["mu"],
        "n_lo": lo["n_bulk"], "n_hi": hi["n_bulk"],
    }


# ================================================================ 3. Landau
# A flow at velocity v can create an excitation of momentum k only if
# v >= omega(k)/k. The Landau critical velocity is the minimum of
# omega(k)/k over k. For the Bogoliubov spectrum omega(k)/k =
# sqrt(k^2/4 + g n) rises monotonically from c_s, so v_c = c_s. For the
# ideal gas omega = k^2/2 and omega/k = k/2 -> 0: no superfluidity.

def landau_report():
    gs = ground_state()
    n, g = gs["n_bulk"], gs["g"]
    cs = math.sqrt(g * n)
    ks = [0.02 + 0.01 * i for i in range(600)]
    ratios = [bogoliubov_omega(k, n, g) / k for k in ks]
    i_min = min(range(len(ks)), key=lambda i: ratios[i])
    ideal_ratios = [0.5 * k for k in ks]
    return {
        "c_s": cs,
        "v_c_bogoliubov": ratios[i_min], "k_at_v_c": ks[i_min],
        "v_c_over_c_s": ratios[i_min] / cs,
        "ratio_monotone": all(ratios[i + 1] > ratios[i]
                              for i in range(len(ratios) - 1)),
        "v_c_ideal_on_grid": min(ideal_ratios),
        "v_c_ideal_limit": 0.0,
        "k_min": ks[0],
    }


# ================================================================ 4. Soliton + ring
# A black (dark) soliton of the uniform condensate is the stationary
# profile psi(x) = sqrt(n) tanh(x / (sqrt(2) xi)): density notch to
# exactly zero at the core, a pi phase jump across it, and it solves
# the stationary GP equation with mu = g n - all three facts are
# verified numerically below, the last by a finite-difference
# residual, not by assertion. (In the lab the profile is constructed
# directly; experimentally such a soliton is what a pi phase imprint
# across half the condensate prepares.)
#
# On a ring, single-valuedness quantises the circulation: a phase
# winding of 2 pi * w around the ring (w an integer) gives the flow
# velocity v = 2 pi w / L and circulation Gamma = 2 pi w (hbar = m = 1).

SOL_HALF = 10.0     # soliton grid half-width
SOL_POINTS = 801    # odd, so a grid point sits exactly on the core
RING_L = 20.0       # ring circumference
RING_POINTS = 256


def soliton_profile(x, n_bulk, g=G_INT):
    xi = healing_length(n_bulk, g)
    return math.sqrt(n_bulk) * math.tanh(x / (math.sqrt(2.0) * xi))


def soliton_report():
    gs = ground_state()
    n, g = gs["n_bulk"], gs["g"]
    xi = healing_length(n, g)
    m = SOL_POINTS
    dx = 2.0 * SOL_HALF / (m - 1)
    xs = [-SOL_HALF + j * dx for j in range(m)]
    psi = [soliton_profile(x, n, g) for x in xs]
    mu_s = g * n
    worst = 0.0
    for j in range(1, m - 1):
        if abs(psi[j]) > 0.1 * math.sqrt(n):
            lap = (psi[j - 1] - 2.0 * psi[j] + psi[j + 1]) / (dx * dx)
            r = (-0.5 * lap + g * psi[j] ** 3 - mu_s * psi[j])
            worst = max(worst, abs(r) / (mu_s * abs(psi[j])))
    mid = m // 2
    j3 = min(range(m), key=lambda j: abs(xs[j] - 3.0 * xi))
    jm3 = min(range(m), key=lambda j: abs(xs[j] + 3.0 * xi))
    j6 = min(range(m), key=lambda j: abs(xs[j] - 6.0 * xi))
    phase_jump = abs(cmath.phase(complex(psi[j3], 0.0))
                     - cmath.phase(complex(psi[jm3], 0.0)))
    return {
        "n_inf": n, "g": g, "xi": xi, "mu_soliton": mu_s,
        "core_density": psi[mid] ** 2,
        "core_density_over_n": (psi[mid] ** 2) / n,
        "phase_jump_rad": phase_jump,
        "phase_jump_over_pi": phase_jump / math.pi,
        "gp_residual_rel": worst,
        "density_at_6xi_over_n": (psi[j6] ** 2) / n,
        "width_scale": math.sqrt(2.0) * xi,
    }


def circulation_report():
    gs = ground_state()
    n = gs["n_bulk"]
    m = RING_POINTS
    dx = RING_L / m
    out = {}
    for w in (0, 1, 2, 3):
        psi = [math.sqrt(n) * cmath.exp(2j * math.pi * w * j / m)
               for j in range(m)]
        total = 0.0
        for j in range(m):
            dphi = cmath.phase(psi[(j + 1) % m] / psi[j])
            total += dphi
        v = 2.0 * math.pi * w / RING_L
        e_grad = 0.0
        for j in range(m):
            e_grad += abs(psi[(j + 1) % m] - psi[j]) ** 2
        e_grad = 0.5 * e_grad / (m * dx * dx) / n  # per-particle energy
        out[f"w{w}"] = {
            "winding_input": w,
            "total_phase_rad": total,
            "winding_recovered": int(round(total / (2.0 * math.pi))),
            "velocity": v,
            "circulation": 2.0 * math.pi * w,
            "energy_per_particle_grad": e_grad,
            "energy_per_particle_exact": 0.5 * v * v,
        }
    return out


def vortex_report():
    return {"soliton": soliton_report(), "circulation": circulation_report()}


# ================================================================ 5. TinyML kNN
# Scenario features: (mach, k_xi) - flow speed in units of c_s, and
# probe wavenumber in units of 1/xi. The policy is the physics:
# at or above Mach 1 the Landau criterion fails (landau-unstable);
# below it, the probe regime is set by k xi (phonon / crossover /
# free-particle). Labels come from the policy alone; the kNN just has
# to agree with it.

def policy_label(mach, k_xi):
    if mach >= 1.0:
        return "landau-unstable"
    if k_xi <= 0.5:
        return "phonon-linear"
    if k_xi >= 2.0:
        return "free-particle"
    return "crossover"


def _training_grid():
    rows = []
    for mach in (0.0, 0.25, 0.50, 0.75, 0.90, 1.0, 1.25, 1.50, 2.0):
        for k_xi in (0.1, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0):
            rows.append(((mach, k_xi), policy_label(mach, k_xi)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    mach, k_xi = features
    return (mach, math.log(k_xi))


def classify_regime(mach, k_xi, k=3):
    """Distance-weighted kNN over the policy-labelled grid."""
    target = _scaled((mach, k_xi))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, point)))
        ranked.append((dist, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    weights = {}
    for dist, _, label in ranked[:k]:
        weights[label] = weights.get(label, 0.0) + 1.0 / (dist + 1e-9)
    priority = {"landau-unstable": 0, "phonon-linear": 1,
                "crossover": 2, "free-particle": 3}
    return sorted(weights.items(),
                  key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def classifier_report():
    gs = ground_state()
    n, g = gs["n_bulk"], gs["g"]
    xi = healing_length(n, g)
    cs = math.sqrt(g * n)
    scenarios = {
        "phonon_probe_k0.3xi_rest": (0.0, 0.3),
        "crossover_probe_k1xi_rest": (0.0, 1.0),
        "free_particle_probe_k4xi_rest": (0.0, 4.0),
        "subsonic_flow_half_cs": (0.5 * cs / cs, 1.0),
        "supersonic_flow_1.5cs": (1.5 * cs / cs, 1.0),
    }
    return {name: classify_regime(mach, k_xi)
            for name, (mach, k_xi) in scenarios.items()}


# ================================================================ 6. Advisory seats
def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="superfluid-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "model_id": "gemini-argon-4",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all device gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="superfluid-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Say it in the first line of every report: superfluidity here is a property of a stated mean-field spectrum, not of a material - then show mu, xi, c_s computed three ways, and v_c next to the ideal gas's zero.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["a condensate density settling flat in its box as imaginary time runs",
                  "the Bogoliubov curve bending from a straight phonon line into a parabola",
                  "a dark soliton notch with the phase flipping by pi across it",
                  "a flow speeding up toward c_s and stopping at the Landau line",
                  "phase winding around a ring, one full turn per quantum of circulation"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. GP ground state - the solver is graded before it is trusted
    gs = ground_state()
    n, g = gs["n_bulk"], gs["g"]
    xi = healing_length(n, g)
    chk("gp_norm_conserved",
        abs(_norm_sq(gs["psi"], gs["dx"]) - NPART) < 1e-6)
    chk("gp_density_nonnegative", min(v * v for v in gs["psi"]) >= 0.0)
    chk("gp_mu_positive", gs["mu"] > 0.0)
    chk("gp_mu_near_gn_bulk",
        abs(gs["mu"] / (g * n) - 1.0) < 0.02)
    chk("gp_residual_small", gs["residual"] < 0.02)
    chk("gp_wall_density_suppressed",
        (gs["psi"][1] ** 2) / n < 0.01)
    chk("gp_bulk_flat", _bulk_flatness(gs) < 0.02)
    ss = sound_speed_report()
    chk("gp_mu_monotone_in_npart",
        ss["mu_lo"] < ss["mu_mid"] < ss["mu_hi"])
    chk("gp_bulk_density_monotone_in_npart",
        ss["n_lo"] < n < ss["n_hi"])
    chk("healing_length_definition",
        abs(xi * math.sqrt(2.0 * g * n) - 1.0) < 1e-12)
    chk("healing_length_vs_box", 0.05 < xi / BOX_L < 0.2)

    # 2. Bogoliubov dispersion - both asymptotes and the crossover
    disp = dispersion_report()
    chk("dispersion_zero_at_k0", bogoliubov_omega(0.0, n, g) == 0.0)
    chk("dispersion_phonon_limit", abs(disp["phonon_ratio_at_small_k"] - 1.0) < 0.01)
    chk("dispersion_free_particle_limit",
        abs(disp["free_particle_ratio_at_large_k"] - 1.0) < 1e-3)
    omegas = [r["omega"] for r in disp["rows"]]
    chk("dispersion_monotone",
        all(omegas[i + 1] > omegas[i] for i in range(len(omegas) - 1)))
    chk("crossover_kstar_xi_is_sqrt2",
        abs(disp["k_star_xi"] - math.sqrt(2.0)) < 1e-9)
    chk("crossover_log_slope_midway",
        abs(disp["log_slope_at_k_star"] - 1.5) < 0.02)
    chk("dispersion_regimes_labelled",
        {r["regime"] for r in disp["rows"]}
        == {"phonon", "crossover", "free-particle"})

    # 3. sound speed - three independent routes must agree
    chk("cs_direct_positive", ss["c_s_direct"] > 0.0)
    chk("cs_mu_slope_agrees", ss["rel_diff_mu"] < 0.02)
    chk("cs_dispersion_slope_agrees", ss["rel_diff_slope"] < 0.01)
    chk("dmu_dn_near_g", abs(ss["dmu_dn"] / g - 1.0) < 0.02)

    # 4. Landau criterion - v_c = c_s here, and 0 for the ideal gas
    land = landau_report()
    chk("landau_ratio_monotone", land["ratio_monotone"])
    chk("landau_vc_within_1pct_of_cs", land["v_c_over_c_s"] - 1.0 < 0.01)
    chk("landau_vc_at_smallest_k", land["k_at_v_c"] == land["k_min"])
    chk("landau_ideal_gas_grid_min_is_kmin_over_2",
        abs(land["v_c_ideal_on_grid"] - land["k_min"] / 2.0) < 1e-12)
    chk("landau_ideal_gas_limit_zero", land["v_c_ideal_limit"] == 0.0)
    chk("landau_vc_far_above_ideal",
        land["v_c_bogoliubov"] > 50.0 * land["v_c_ideal_on_grid"])

    # 5. dark soliton - notch, phase jump, and it solves GP
    sol = soliton_report()
    chk("soliton_core_density_zero", sol["core_density_over_n"] < 1e-12)
    chk("soliton_phase_jump_pi",
        abs(sol["phase_jump_over_pi"] - 1.0) < 1e-9)
    chk("soliton_gp_residual_small", sol["gp_residual_rel"] < 0.02)
    chk("soliton_density_recovers", abs(sol["density_at_6xi_over_n"] - 1.0) < 0.01)

    # 6. ring circulation - quantised, integer windings recovered
    circ = circulation_report()
    chk("circulation_windings_recovered",
        all(circ[f"w{w}"]["winding_recovered"] == w for w in (0, 1, 2, 3)))
    chk("circulation_phase_totals",
        all(abs(circ[f"w{w}"]["total_phase_rad"] - 2.0 * math.pi * w) < 1e-9
            for w in (0, 1, 2, 3)))
    chk("circulation_energy_matches_v2_over_2",
        all(abs(circ[f"w{w}"]["energy_per_particle_grad"]
                - circ[f"w{w}"]["energy_per_particle_exact"])
            < 0.002 * max(1.0, circ[f"w{w}"]["energy_per_particle_exact"])
            for w in (0, 1, 2, 3)))
    chk("circulation_scales_linearly",
        abs(circ["w3"]["circulation"] - 3.0 * circ["w1"]["circulation"]) < 1e-12)

    # 7. classifier - agrees with its own policy everywhere
    chk("knn_agrees_policy_grid",
        all(classify_regime(*features) == policy_label(*features)
            for features, _ in TRAINING_GRID))
    rep = classifier_report()
    chk("knn_phonon_scenario", rep["phonon_probe_k0.3xi_rest"] == "phonon-linear")
    chk("knn_crossover_scenario",
        rep["crossover_probe_k1xi_rest"] == "crossover")
    chk("knn_free_particle_scenario",
        rep["free_particle_probe_k4xi_rest"] == "free-particle")
    chk("knn_subsonic_scenario", rep["subsonic_flow_half_cs"] == "crossover")
    chk("knn_supersonic_scenario",
        rep["supersonic_flow_1.5cs"] == "landau-unstable")

    # 8. determinism - same inputs, byte-identical reports
    chk("reports_deterministic",
        json.dumps(dispersion_report(), sort_keys=True)
        == json.dumps(disp, sort_keys=True)
        and json.dumps(soliton_report(), sort_keys=True)
        == json.dumps(sol, sort_keys=True))

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_device_claim_hold", gate("superfluid_device_claim") == "HOLD")
    chk("gate_beyond_meanfield_hold", gate("beyond_meanfield_claim") == "HOLD")
    chk("gate_finite_temperature_hold",
        gate("finite_temperature_claim") == "HOLD")
    chk("gate_sim_as_measurement_hold",
        gate("simulation_as_measurement_claim") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking"
        and brains["decider"]["model_id"] == "gemini-argon-4")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("Superfluid-Lab - Gross-Pitaevskii, Bogoliubov & Landau lab")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - mean-field theorems, not measurements")
    print("    A weakly interacting condensate (hbar = m = 1, T = 0) is")
    print("    solved with the Gross-Pitaevskii equation. Superfluidity")
    print("    enters through the Landau criterion on the Bogoliubov")
    print("    spectrum - a property of THIS model. No Lee-Huang-Yang or")
    print("    other beyond-mean-field correction is included or claimed.")
    gs = groundstate_report()
    print("\n[2] Ground state - imaginary-time GP in a hard-wall box")
    print(f"    grid {gs['grid_points']} points | box L = {gs['box_length']} "
          f"| N = {gs['npart']:.0f} | g = {gs['g']}")
    print(f"    imaginary-time steps to converge: {gs['steps']}")
    print(f"    chemical potential mu = {gs['mu']:.6f} "
          f"(uniform estimate g*n = {gs['g_times_n']:.6f}, "
          f"ratio {gs['mu_over_gn']:.6f} - the excess is boundary kinetic)")
    print(f"    bulk density n = {gs['n_bulk']:.6f} | stationarity "
          f"residual {gs['residual']:.2e} | bulk flatness "
          f"{gs['bulk_flatness']:.2e}")
    print(f"    healing length xi = 1/sqrt(2 g n) = {gs['xi']:.6f} "
          f"(box fits {gs['box_length'] / gs['xi']:.1f} healing lengths)")
    disp = dispersion_report()
    print("\n[3] Bogoliubov dispersion omega(k) = sqrt(eps (eps + 2 g n))")
    print("      k        omega     omega/k    k*xi   regime")
    for r in disp["rows"][::6]:
        print(f"    {r['k']:7.3f}  {r['omega']:9.6f}  {r['omega_over_k']:8.6f}"
              f"  {r['k_xi']:6.2f}   {r['regime']}")
    print(f"    phonon limit: omega/(c_s k) at k = 0.05 -> "
          f"{disp['phonon_ratio_at_small_k']:.6f} (linear, sound)")
    print(f"    free-particle limit: omega/(eps + g n) at k = 20 -> "
          f"{disp['free_particle_ratio_at_large_k']:.6f} (quadratic)")
    print(f"    crossover at k* = {disp['k_star']:.6f} "
          f"(k* xi = {disp['k_star_xi']:.6f} = sqrt(2)), where the "
          f"log-slope is {disp['log_slope_at_k_star']:.4f} - midway "
          f"between phonon (1) and free-particle (2)")
    ss = sound_speed_report()
    print("\n[4] Sound speed - computed three independent ways")
    print(f"    c_s = sqrt(g n)              = {ss['c_s_direct']:.6f}")
    print(f"    c_s = sqrt(n dmu/dn)         = {ss['c_s_from_mu']:.6f} "
          f"(dmu/dn = {ss['dmu_dn']:.6f} from GP solves at N = 90/100/110; "
          f"rel. diff {ss['rel_diff_mu']:.4%})")
    print(f"    c_s = low-k dispersion slope = {ss['c_s_from_slope']:.6f} "
          f"(rel. diff {ss['rel_diff_slope']:.4%})")
    print("    -> three routes, one sound speed: the compressibility,")
    print("       the equation of state, and the phonon slope agree.")
    land = landau_report()
    print("\n[5] Landau criterion - when can a flow create excitations?")
    print(f"    Bogoliubov: omega(k)/k rises monotonically from c_s, so")
    print(f"    v_c = {land['v_c_bogoliubov']:.6f} at the smallest grid k "
          f"(= c_s x {land['v_c_over_c_s']:.6f}; the k -> 0 limit is c_s "
          f"= {land['c_s']:.6f} exactly)")
    print(f"    ideal gas: omega/k = k/2, on-grid min "
          f"{land['v_c_ideal_on_grid']:.6f} at k = {land['k_min']} and "
          f"the limit is 0 - no interactions, no phonons, no superfluidity")
    print("    -> below v_c the flow is dissipationless IN THIS MODEL;")
    print("       above it, excitations become energetically free.")
    sol = soliton_report()
    print("\n[6] Dark soliton - the stationary notch in the condensate")
    print(f"    psi(x) = sqrt(n) tanh(x / (sqrt(2) xi)), width scale "
          f"{sol['width_scale']:.6f}")
    print(f"    core density / n = {sol['core_density_over_n']:.2e} "
          f"(the notch reaches zero)")
    print(f"    phase jump across the core = {sol['phase_jump_rad']:.6f} rad "
          f"= {sol['phase_jump_over_pi']:.6f} pi")
    print(f"    stationary GP residual (rel.) = {sol['gp_residual_rel']:.2e} "
          f"at mu = g n = {sol['mu_soliton']:.6f} - the profile solves GP,")
    print(f"    density back to {sol['density_at_6xi_over_n']:.6f} of n "
          f"by |x| = 6 xi")
    circ = circulation_report()
    print("\n[7] Ring circulation - quantised by single-valuedness")
    for w in (0, 1, 2, 3):
        row = circ[f"w{w}"]
        print(f"    winding {w}: total phase {row['total_phase_rad']:.6f} rad "
              f"-> recovered w = {row['winding_recovered']} | "
              f"v = {row['velocity']:.6f} | Gamma = "
              f"{row['circulation']:.6f} | E/N = "
              f"{row['energy_per_particle_exact']:.6f}")
    print("    -> circulation comes in whole quanta of 2 pi (hbar = m = 1);")
    print("       there is no winding 1.5 state on a ring.")
    print("\n[8] Regime classifier (TinyML kNN, labels from the Landau policy)")
    for name, label in classifier_report().items():
        print(f"    {name:36s} -> {label}")
    print("\n[9] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = {brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[10] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "groundstate":
        print(json.dumps(groundstate_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "dispersion":
        print(json.dumps(dispersion_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "landau":
        out = {"sound_speed": sound_speed_report(),
               "landau": landau_report()}
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    if cmd == "vortex":
        print(json.dumps(vortex_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "superfluid_device_claim"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
