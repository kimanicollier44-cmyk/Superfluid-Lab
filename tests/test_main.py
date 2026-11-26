"""Tests for Superfluid-Lab. Every test grades a computed number
against a closed form or an independent route in main.py."""
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main as sf


def test_gp_norm_conserved():
    gs = sf.ground_state()
    assert abs(sf._norm_sq(gs["psi"], gs["dx"]) - sf.NPART) < 1e-6


def test_gp_mu_near_uniform_estimate():
    gs = sf.ground_state()
    ratio = gs["mu"] / (gs["g"] * gs["n_bulk"])
    assert 1.0 < ratio < 1.02


def test_gp_residual_small():
    assert sf.ground_state()["residual"] < 0.02


def test_gp_bulk_flat_and_wall_suppressed():
    gs = sf.ground_state()
    assert sf._bulk_flatness(gs) < 0.02
    assert (gs["psi"][1] ** 2) / gs["n_bulk"] < 0.01


def test_gp_mu_monotone_in_npart():
    ss = sf.sound_speed_report()
    assert ss["mu_lo"] < ss["mu_mid"] < ss["mu_hi"]
    assert ss["n_lo"] < ss["n_bulk"] < ss["n_hi"]


def test_healing_length_definition():
    gs = sf.ground_state()
    xi = sf.healing_length(gs["n_bulk"], gs["g"])
    assert abs(xi * math.sqrt(2.0 * gs["g"] * gs["n_bulk"]) - 1.0) < 1e-12


def test_dispersion_endpoints():
    gs = sf.ground_state()
    n, g = gs["n_bulk"], gs["g"]
    assert sf.bogoliubov_omega(0.0, n, g) == 0.0
    k = 3.7
    eps = 0.5 * k * k
    assert abs(sf.bogoliubov_omega(k, n, g)
               - math.sqrt(eps * (eps + 2.0 * g * n))) < 1e-12


def test_dispersion_phonon_and_free_limits():
    disp = sf.dispersion_report()
    assert abs(disp["phonon_ratio_at_small_k"] - 1.0) < 0.01
    assert abs(disp["free_particle_ratio_at_large_k"] - 1.0) < 1e-3


def test_crossover_scale_and_slope():
    disp = sf.dispersion_report()
    assert abs(disp["k_star_xi"] - math.sqrt(2.0)) < 1e-9
    assert abs(disp["log_slope_at_k_star"] - 1.5) < 0.02


def test_sound_speed_three_ways_agree():
    ss = sf.sound_speed_report()
    assert ss["rel_diff_mu"] < 0.02
    assert ss["rel_diff_slope"] < 0.01
    assert abs(ss["dmu_dn"] / sf.G_INT - 1.0) < 0.02


def test_landau_vc_is_cs():
    land = sf.landau_report()
    assert land["ratio_monotone"]
    assert 1.0 <= land["v_c_over_c_s"] < 1.01


def test_landau_ideal_gas_zero():
    land = sf.landau_report()
    assert land["v_c_ideal_limit"] == 0.0
    assert abs(land["v_c_ideal_on_grid"] - land["k_min"] / 2.0) < 1e-12
    assert land["v_c_bogoliubov"] > 50.0 * land["v_c_ideal_on_grid"]


def test_soliton_notch_and_phase():
    sol = sf.soliton_report()
    assert sol["core_density_over_n"] < 1e-12
    assert abs(sol["phase_jump_over_pi"] - 1.0) < 1e-9
    assert abs(sol["density_at_6xi_over_n"] - 1.0) < 0.01


def test_soliton_solves_gp():
    assert sf.soliton_report()["gp_residual_rel"] < 0.02


def test_circulation_quantised():
    circ = sf.circulation_report()
    for w in (0, 1, 2, 3):
        row = circ[f"w{w}"]
        assert row["winding_recovered"] == w
        assert abs(row["total_phase_rad"] - 2.0 * math.pi * w) < 1e-9
        assert abs(row["circulation"] - 2.0 * math.pi * w) < 1e-12


def test_circulation_energy():
    circ = sf.circulation_report()
    for w in (1, 2, 3):
        row = circ[f"w{w}"]
        v = 2.0 * math.pi * w / sf.RING_L
        assert abs(row["energy_per_particle_exact"] - 0.5 * v * v) < 1e-12
        assert abs(row["energy_per_particle_grad"]
                   - row["energy_per_particle_exact"]) < 0.002


def test_knn_agrees_with_policy():
    for features, _ in sf.TRAINING_GRID:
        assert sf.classify_regime(*features) == sf.policy_label(*features)


def test_classifier_scenarios():
    rep = sf.classifier_report()
    assert rep["phonon_probe_k0.3xi_rest"] == "phonon-linear"
    assert rep["crossover_probe_k1xi_rest"] == "crossover"
    assert rep["free_particle_probe_k4xi_rest"] == "free-particle"
    assert rep["supersonic_flow_1.5cs"] == "landau-unstable"


def test_hold_gates():
    assert len(sf.HOLD_GATES) == 14
    assert sf.gate("superfluid_device_claim") == "HOLD"
    assert sf.gate("beyond_meanfield_claim") == "HOLD"
    assert sf.gate("finite_temperature_claim") == "HOLD"
    assert sf.gate("run_simulation") == "PROCEED"


def test_council_seats():
    brains = sf.brains_report()
    assert brains["decider"]["can_override_hold"] is False
    assert brains["decider"]["model_id"] == "gemini-argon-4"
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False
    assert brains["flow"]["live"] == 0


def test_hold_demo_exits_2():
    root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, str(root / "main.py"), "hold-demo"],
        capture_output=True, text=True)
    assert proc.returncode == 2
    assert "HOLD" in proc.stdout


def test_reports_deterministic():
    import json
    a = json.dumps(sf.dispersion_report(), sort_keys=True)
    b = json.dumps(sf.dispersion_report(), sort_keys=True)
    assert a == b
