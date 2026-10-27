"""Screen power margins and converter sensitivities without hardware readings.

Run with ordinary Python after the CAD-derived power/load checks. Every
temperature, loss and capacitance scenario is an assumption, not a rating.
This script does not change CAD or certify a fabrication release.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def feedback_network(top, bottom, capacitance_pf, frequency_hz):
    """Phase lead of the passive divider only; not converter phase margin."""
    c = capacitance_pf * 1e-12
    parallel = top * bottom / (top + bottom)
    zero = 1 / (2 * math.pi * top * c)
    pole = 1 / (2 * math.pi * parallel * c)
    phase = math.degrees(math.atan(frequency_hz / zero) -
                         math.atan(frequency_hz / pole))
    return zero, pole, phase


def buck_scenario(vin, vout, current, inductance, frequency,
                  resistance_multiplier, overlap_ns):
    """Ideal CCM duty/ripple; overlap-time and hot-RDSon are assumptions."""
    if not (0 < vout < vin and current >= 0 and inductance > 0 and frequency > 0):
        raise ValueError("Buck calculation requires 0 < Vout < Vin and positive L/f")
    duty = vout / vin
    ripple = vout * (1 - duty) / (inductance * frequency)
    common = {
        "vin_V": vin, "vout_V": vout, "current_A": current,
        "inductance_uH_assumed": inductance * 1e6, "frequency_Hz": frequency,
        "RDSon_multiplier_assumed": resistance_multiplier,
        "total_switch_overlap_ns_assumed": overlap_ns,
        "duty_ideal": duty, "CCM_candidate_ripple_A_pp": ripple,
        "ccm_assumption_valid": current > ripple / 2,
    }
    # TPS564252 is Eco-mode: negative CCM valley estimates are not physical
    # predictions of its light-load behavior. Do not use them in extrema.
    if not common["ccm_assumption_valid"]:
        return common
    conduction = (current**2 + ripple**2 / 12) * resistance_multiplier * (
        duty * .055 + (1 - duty) * .0243)
    overlap = .5 * vin * current * overlap_ns * 1e-9 * frequency
    return {
        **common, "ripple_A_pp": ripple,
        "peak_A": current + ripple / 2,
        "valley_A": current - ripple / 2,
        "input_cap_ripple_A_rms_ideal": math.sqrt(
            current**2 * duty * (1 - duty) + duty * ripple**2 / 12),
        "output_cap_ripple_A_rms_ideal": ripple / math.sqrt(12),
        "conduction_W": conduction, "switch_overlap_W_assumed": overlap,
        "modeled_IC_loss_W_NOT_total": conduction + overlap,
        "inductor_copper_W_at_25C_DCR_upper_23p4mohm":
            (current**2 + ripple**2 / 12) * .0234,
        "required_effective_theta_at_40C_C_per_W_before_other_losses":
            85 / (conduction + overlap),
    }


def calculate():
    power, allocation = read("Power-stage-check.json"), read("Load-allocation-check.json")
    design, supply = read("Power-calculations.json"), read("Supply-path-check.json")
    board_hash = digest(ROOT / "KiCad/Lab4.kicad_pcb")
    assert power["source_sha256"]["KiCad/Lab4.kicad_pcb"] == board_hash
    assert allocation["source_sha256"] == supply["source_sha256"] == board_hash
    for name, expected in power["source_sha256"].items():
        assert digest(ROOT / name) == expected, f"Regenerate power check: {name}"
    with (ROOT / "KiCad/Circuit-BOM.csv").open(encoding="utf-8-sig", newline="") as stream:
        parts = {row["Reference"]: row for row in csv.DictReader(stream)}
    assert design["protected_input_design_range_V"] == [8, 15], "Update the sensitivity grid"
    assert parts["U80"]["MPN"] == "L298N", "Update the motor-driver model"

    # Do not confuse nominal voltage, an operating limit and a warning threshold.
    targets = [
        ("CAN", "logic", ["U11", "U15", "U21", "U25", "U31", "U35"], 3.0,
         "SN65HVD231 recommended VCC minimum"),
        ("Encoders", "logic", ["J82", "J83"], 3.3,
         "Recorded motor specification's 3.3-5V range; endpoint tolerance unknown"),
        ("Pi warning screen", "five_volt", ["J70"], 4.63 * 1.05,
         "Upper end of documented 4.63V +/-5% low-voltage detector; not a minimum operating specification"),
    ]
    voltage = []
    for name, rail, refs, floor, meaning in targets:
        loads = [x for x in allocation[rail]["loads"] if x["ref"] in refs]
        worst = max(loads, key=lambda x: x["shared_tree_drop_V"])
        source = allocation[rail]["source_minimum_V"]
        for factor in (1.0, 1.45, 1.8):
            headroom = source - factor * worst["shared_tree_drop_V"] - floor
            voltage.append({
                "group": name, "target_ref": worst["ref"],
                "comparison_voltage_V": floor, "comparison_meaning": meaning,
                "conductor_R_multiplier_assumed": factor,
                "source_minimum_V": source,
                "positive_feed_drop_V": factor * worst["shared_tree_drop_V"],
                "budget_for_ALL_remaining_losses_V": headroom,
                "load_voltage_with_assumed_50mV_return_V": headroom + floor - .05,
            })

    converter = []
    for i, stage in enumerate(power["regulators"]):
        setting = design["regulators"][i]
        assert stage["rail"] == setting["rail"]
        assert setting["inductance_uH"] == 4.7
        assert stage["allocated_output_A"] == setting["allocation_A"]
        base = 410 + 10*i
        assert parts[f"U{40+i}"]["MPN"] == "TPS564252DRLR"
        assert parts[f"L{i+1}"]["MPN"] == "SDCHA1V8040-4R7-R"
        assert parts[f"C{base}"]["MPN"] == "GRM32ER61E226KE15L"
        for ref in (f"C{base+2}", f"C{base+3}"):
            assert parts[ref]["MPN"] == "GRM219R61C226ME15L"
        vout, current = stage["output_nominal_V"], stage["allocated_output_A"]
        inductance = setting["inductance_uH"] * 1e-6 * .8
        voltages = [stage["static_reference_and_resistor_corners_V"][0], vout,
                    stage["static_reference_and_resistor_corners_V"][1]]
        raw_cases = [buck_scenario(vin, voltage, current, ls, frequency, hot, ns)
                 for vin in (8, 12, 15)
                 for voltage in voltages
                 for ls in (inductance, 2.63e-6)
                 for frequency in (400000, 600000, 800000)
                 for hot in (1.0, 1.5, 2.0)
                 for ns in (10, 20, 40)]
        cases = [x for x in raw_cases if x["ccm_assumption_valid"]]
        typical_r = [x for x in cases if x["RDSon_multiplier_assumed"] == 1
                     and x["frequency_Hz"] == 600000
                     and x["vout_V"] == vout
                     and math.isclose(x["inductance_uH_assumed"], inductance*1e6)]
        top, bottom = setting["feedback_top_ohm"], setting["feedback_bottom_ohm"]
        feedback = []
        for c in (22, 30, 82, 91):
            zero, pole, phase = feedback_network(top, bottom, c, 66000)
            feedback.append({"Cff_pF": c, "zero_Hz": zero, "pole_Hz": pole,
                             "divider_phase_lead_at_66kHz_deg": phase})
        capacitor = []
        for effective in (11, 16.842, 22, 29.92, 44):
            for frequency in (400000, 600000):
                case = buck_scenario(15, vout, current, inductance, frequency, 1, 0)
                valid = case["ccm_assumption_valid"]
                ripple = case["CCM_candidate_ripple_A_pp"]
                capacitor.append({
                    "effective_total_uF_assumed": effective,
                    "frequency_Hz_assumed": frequency,
                    "LC_pole_Hz_low_L": 1/(2*math.pi*math.sqrt(inductance*effective*1e-6)),
                    "ccm_assumption_valid": valid,
                    "capacitive_ripple_V_pp_ideal": ripple/(8*frequency*effective*1e-6) if valid else None,
                    "extra_ripple_V_pp_if_total_ESR_is_10mohm": ripple*.01 if valid else None,
                    "droop_per_1A_step_10us_before_response_V": .00001/(effective*1e-6),
                })
        converter.append({
            "reference": stage["reference"], "rail": stage["rail"],
            "grid": {"vin_V": [8, 12, 15], "vout_V": voltages,
                     "inductance_uH_assumed": [inductance*1e6, 2.63],
                     "frequency_Hz_assumed": [400000, 600000, 800000],
                     "RDSon_multiplier_assumed": [1, 1.5, 2],
                     "total_switch_overlap_ns_assumed": [10, 20, 40]},
            "number_of_cases": len(raw_cases),
            "number_of_excluded_non_CCM_cases": len(raw_cases)-len(cases),
            "extreme_cases": {
                label: max(cases, key=lambda x: x[field]) for label, field in [
                    ("highest_modeled_IC_loss", "modeled_IC_loss_W_NOT_total"),
                    ("highest_input_cap_ripple", "input_cap_ripple_A_rms_ideal"),
                    ("highest_output_cap_ripple", "output_cap_ripple_A_rms_ideal"),
                    ("highest_inductor_peak", "peak_A"),
                    ("highest_valley", "valley_A")]},
            "passive_feedback_network": feedback,
            "capacitor_sensitivity": capacitor,
            "max_conduction_25C_typ_R_600kHz_over_8to15V_W": max(x["conduction_W"] for x in typical_r),
            "max_scenario_IC_loss_W_NOT_guaranteed": max(x["modeled_IC_loss_W_NOT_total"] for x in cases),
            "largest_input_cap_ripple_A_rms_in_grid": max(x["input_cap_ripple_A_rms_ideal"] for x in cases),
            "largest_output_cap_ripple_A_rms_in_grid": max(x["output_cap_ripple_A_rms_ideal"] for x in cases),
            "max_current_peak_A_in_valid_CCM_grid": max(x["peak_A"] for x in cases),
            "max_inductor_copper_loss_25C_W_in_valid_CCM_grid": max(
                x["inductor_copper_W_at_25C_DCR_upper_23p4mohm"] for x in cases),
            "largest_valley_A_in_grid": max(x["valley_A"] for x in cases),
            "min_required_theta_at_40C_C_per_W_in_grid": min(
                x["required_effective_theta_at_40C_C_per_W_before_other_losses"] for x in cases),
            "output_charge_current_44uF_1p6ms_linear_ramp_A": 44e-6*vout/.0016,
        })

    return {
        "status": "Calculations complete; design margins NOT qualified",
        "fabrication_release": False,
        "sources": [
            "https://www.ti.com/lit/ds/symlink/tps564252.pdf",
            "https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-sdcha1v80-automotive-semi-shielded-power-inductor-data-sheet-elx1097-en.pdf",
            "https://www.mouser.com/datasheet/2/281/1/GRM219R61C226ME15_01A-1986409.pdf",
            "https://www.farnell.com/datasheets/4088151.pdf",
            "https://www.raspberrypi.com/documentation/computers/raspberry-pi.html",
            "https://www.ti.com/lit/ds/symlink/sn65hvd231.pdf",
            "doc/HARDWARE.md (encoder range in recorded motor specification)",
            "https://www.st.com/resource/en/datasheet/l298.pdf",
            "https://www.farnell.com/datasheets/1581373.pdf"],
        "source_sha256": {name: digest(ROOT / name) for name in [
            "KiCad/Lab4.kicad_pcb", "Power-stage-check.json", "Power-calculations.json",
            "Load-allocation-check.json", "Supply-path-check.json", "check_power_margins.py",
            "KiCad/Circuit-BOM.csv"]},
        "voltage_budget": voltage, "converters": converter,
        "thermal_loss_budgets_W": [
            {"ambient_C_assumed": ambient, "theta_C_per_W_assumed": theta,
             "maximum_total_IC_loss_W_for_125C": (125-ambient)/theta}
            for ambient in (25, 40, 60) for theta in (74, 100, 150)],
        "L298_steady_conduction_screens_NOT_permitted_loads": [
            {"current_A_each_of_two_bridges": amps,
             "ST_total_bridge_drop_max_V_at_25C_test": drop,
             "two_bridge_conduction_W": 2*amps*drop,
             "target_junction_C_assumed": 125, "ambient_C_assumed": 40,
             "interface_theta_C_per_W_assumed": 1,
             "maximum_sink_theta_C_per_W_before_other_losses":
                 85/(2*amps*drop)-3-1}
            for amps, drop in [(1, 3.2), (2, 4.9)]],
        "capacitor_retention_requirements": {
            "output_44uF_after_minus20percent_tolerance_minus15percent_temp_uF": 29.92,
            "combined_bias_aging_retention_for_16p842uF": 16.842/29.92,
            "input_22uF_after_minus10percent_tolerance_minus15percent_temp_uF": 16.83,
            "combined_bias_aging_retention_for_10uF_input": 10/16.83,
            "total_output_uF_for_20kHz_with_2p63uH_assumed":
                1e6 / ((2*math.pi*20000)**2 * 2.63e-6),
            "meaning": "Conditional screening targets, not measured retention or guaranteed combination rules"},
        "ground_sheet_sensitivity": [
            {"squares_assumed": squares, "current_A_assumed": amps,
             "drop_V_at_20C_nominal_15p2um": 1.72e-8/15.2e-6*squares*amps}
            for squares in (1, 5, 10) for amps in (.8, 3, 10)],
        "limitations": [
            "Positive routing is the prior conductor-tree screen, not a nodal copper solve. Ground sheet examples are NOT extracted from board geometry.",
            "All R multipliers, 50mV return, ambient temperatures and thermal resistances are sensitivity assumptions; none is a measured or guaranteed bound.",
            "400-800kHz, RDSon multipliers and 10-40ns overlap are assumed sweeps. Datasheet switching frequency and resistances are typical, not max bounds.",
            "2.63uH is Eaton's full-load minimum at 6.7A and 25C; using it at our loads is a rolloff sensitivity, not a guaranteed minimum over all temperatures/faults.",
            "Loss omits gate drive, Coss, dead time, reverse recovery, control losses and external inductor/core/capacitor losses. No junction-temperature prediction is made.",
            "Ideal CCM ripple/loss cases with zero or negative inductor valley are excluded: Eco-mode/DCM requires a different model. Extrema cover valid CCM scenarios only, not every possible operating mode.",
            "Ideal CCM capacitor-ripple and charge-step equations exclude loop response, ESR/ESL, pulse-skipping and unequal sharing. Inductor copper loss uses 19.5mohm +20% at 25C and omits core/hot losses.",
            "Divider phase lead is not full-loop phase margin. Cff alternatives are analysis candidates, not BOM changes.",
            "Exact input/output MLCC bias curves, part-specific aging and PCB thermal impedance are unavailable; no invented values are used.",
            "Battery, protection, mechanical decisions and actual load duty affect final selection. The current 8-15V/allocated-load sweep remains useful before those decisions."],
    }


if __name__ == "__main__":
    result = calculate()
    (ROOT / "Power-margin-check.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "voltage_budget": result["voltage_budget"],
        "converter_summaries": [{k: v for k, v in row.items()
                                 if k not in ("grid", "extreme_cases", "passive_feedback_network", "capacitor_sensitivity")}
                                for row in result["converters"]],
    }, indent=2))
