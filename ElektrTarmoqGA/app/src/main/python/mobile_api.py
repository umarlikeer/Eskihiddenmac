"""Offline API called by the Android UI. Uses the bundled network dataset."""
import json
import os
import traceback
import numpy as np
from ga_core import GAConfig
from ga_optimizer import PowerSystemGA
from opt_q import PowerSystemOptimizer


def _voltages(pso):
    out = []
    for bus in range(1, pso.nuz + 1):
        base = float(pso.u_nominal[bus])
        pu = float(pso.u[bus] / base) if base > 0 else None
        out.append({"bus": bus, "kv": float(pso.u[bus]), "pu": pu})
    return out


def run_optimization(data_path, mode="combined", population=30, generations=30):
    """Run one offline mode and return a JSON string for Kotlin."""
    try:
        if not os.path.isfile(data_path):
            raise FileNotFoundError("DATA_Q14.txt файли топилмади")
        population = max(10, min(int(population), 200))
        generations = max(1, min(int(generations), 500))

        baseline = PowerSystemOptimizer()
        baseline.read_data(data_path)
        baseline.form_y_matrix()
        ok = baseline.calculate_power_system_regime(silent=True, max_iterations=80)
        if not ok:
            raise RuntimeError("Бошланғич электр режими ҳисоблашда яқинлашмади")
        initial_losses = float(baseline.ddp)

        if mode == "baseline":
            return json.dumps({
                "ok": True, "mode": mode, "initial_losses": initial_losses,
                "final_losses": initial_losses, "reduction_mw": 0.0,
                "reduction_percent": 0.0, "initial_voltages": _voltages(baseline),
                "final_voltages": _voltages(baseline), "q_values": {}, "taps": {},
                "violations": [], "generations_run": 0,
                "message": "Бошланғич режим ҳисобланди."
            }, ensure_ascii=False)

        config = GAConfig(population_size=population, max_generations=generations,
                          crossover_prob=0.9, mutation_prob=0.1)
        if mode == "q":
            opt_q, opt_taps = True, False
        elif mode == "taps":
            opt_q, opt_taps = False, True
        elif mode == "combined":
            opt_q, opt_taps = True, True
        else:
            raise ValueError("Номаълум ҳисоблаш режими")

        optimizer = PowerSystemGA(data_file=data_path, ga_config=config,
                                  optimize_q=opt_q, optimize_taps=opt_taps,
                                  verbose=False)
        # A fixed seed makes runs reproducible for the same Python/NumPy version.
        optimizer.ga.rng = np.random.default_rng(42)
        result = optimizer.run()
        final_losses = float(result.final_losses)
        reduction = initial_losses - final_losses
        reduction_percent = 100.0 * reduction / initial_losses if abs(initial_losses) > 1e-12 else 0.0
        final_voltages = _voltages(optimizer.pso)
        initial_voltages = _voltages(baseline)
        q_values = {str(k): float(v) for k, v in result.final_q_values.items()}
        taps = {}
        for branch, vals in result.final_tap_values.items():
            taps[str(branch)] = {"from": int(optimizer.pso.ib[branch]),
                                 "to": int(optimizer.pso.io[branch]),
                                 "kre": float(vals[0]), "kim": float(vals[1])}
        report_path = os.path.join(os.path.dirname(data_path), "natija_optimallashtirish.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Elektr tarmog'ini genetik algoritm bilan optimallashtirish\n")
            f.write(f"Rejim: {mode}\nPopulyatsiya: {population}\nAvlodlar: {generations}\n")
            f.write(f"Boshlang'ich aktiv isrof: {initial_losses:.8f} MW\n")
            f.write(f"Yakuniy aktiv isrof: {final_losses:.8f} MW\n")
            f.write(f"Kamayish: {reduction:.8f} MW ({reduction_percent:.4f} %)\n\n")
            f.write("Tugun kuchlanishlari (p.u.):\n")
            for item in final_voltages:
                f.write(f"{item['bus']}: {item['pu']:.6f}\n")
            f.write("\nQ qiymatlari (MVAr):\n")
            for k, v in q_values.items(): f.write(f"Tugun {k}: {v:.6f}\n")
            f.write("\nTransformator koeffitsientlari:\n")
            for k, v in taps.items(): f.write(f"Shoxobcha {v['from']}-{v['to']}: Kre={v['kre']:.6f}, Kim={v['kim']:.6f}\n")
        return json.dumps({
            "ok": True, "mode": mode, "initial_losses": initial_losses,
            "final_losses": final_losses, "reduction_mw": reduction,
            "reduction_percent": reduction_percent,
            "initial_voltages": initial_voltages, "final_voltages": final_voltages,
            "q_values": q_values, "taps": taps,
            "violations": [{"bus": int(b), "pu": float(v)} for b, v in result.voltage_violations],
            "generations_run": int(result.generations_run),
            "converged": bool(result.converged), "report_path": report_path,
            "message": "Ҳисоблаш тугади. Натижани асл тармоқ модели билан солиштириб текширинг."
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc),
                           "trace": traceback.format_exc()}, ensure_ascii=False)
