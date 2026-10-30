"""Python power-flow solver ported from the supplied OPT_Q Pascal model.

The input format is DATA_Q14.txt. Powers are interpreted as positive for
loads in the source data, so specified net injections are -P and -Q.
The solver uses Newton-Raphson with a numerical Jacobian and the complex-tap
admittance convention present in the original Pascal FormY routine.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
import numpy as np

_NUM = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")


def _numbers(line: str) -> list[float]:
    return [float(x) for x in _NUM.findall(line)]


class PowerSystemOptimizer:
    """Power-flow model compatible with ga_optimizer.py's expected API."""

    def __init__(self):
        self.nuz = 0
        self.mvt = 0
        self.qb = 0
        self.ubu = 0.0
        self.dbu = 0.0
        self.eps = 1e-3
        self.kre_min, self.kre_max = 0.96, 1.12
        self.kim_min, self.kim_max = -0.1, 0.1
        self.ddp = 0.0
        self.ddq = 0.0
        self._loaded = False

    def read_data(self, data_file: str) -> None:
        path = Path(data_file)
        # utf-8-sig handles the supplied text file; replacement avoids legacy
        # malformed characters in section headings.
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        numeric_rows = [(idx, _numbers(line)) for idx, line in enumerate(lines)]
        header_pos = None
        header = None
        for idx, vals in numeric_rows:
            if len(vals) >= 5 and vals[0].is_integer() and vals[1].is_integer():
                n, m = int(vals[0]), int(vals[1])
                if 1 <= n <= 34 and 1 <= m <= 54:
                    header_pos, header = idx, vals[:5]
                    break
        if header_pos is None:
            raise ValueError(f"Could not find network header in {path}")

        self.nuz, self.mvt = int(header[0]), int(header[1])
        self.ubu, self.dbu, self.eps = header[2], header[3], abs(header[4])
        rows_after = numeric_rows
        branch_rows: list[list[float]] = []
        bus_rows: list[list[float]] = []
        q_bounds = None
        tap_bounds = None
        stage = "branches"
        for idx, vals in rows_after:
            if idx <= header_pos or not vals:
                continue
            if stage == "branches":
                if len(vals) >= 8 and len(branch_rows) < self.mvt:
                    branch_rows.append(vals[:8])
                    if len(branch_rows) == self.mvt:
                        stage = "buses"
                continue
            if stage == "buses":
                if len(vals) >= 7 and len(bus_rows) < self.nuz:
                    # Bus records begin with consecutive bus numbers 1..nuz.
                    expected = len(bus_rows) + 1
                    if int(vals[0]) == expected:
                        bus_rows.append(vals[:7])
                    else:
                        continue
                    if len(bus_rows) == self.nuz:
                        stage = "q_bounds"
                continue
            if stage == "q_bounds":
                if len(vals) >= 2:
                    q_bounds = vals[:2]
                    stage = "tap_bounds"
                continue
            if stage == "tap_bounds":
                if len(vals) >= 4:
                    tap_bounds = vals[:4]
                    break

        if len(branch_rows) != self.mvt or len(bus_rows) != self.nuz:
            raise ValueError(
                f"Incomplete network data: expected {self.mvt} branches and "
                f"{self.nuz} buses, read {len(branch_rows)} and {len(bus_rows)}"
            )
        if q_bounds is None or tap_bounds is None:
            raise ValueError("Could not read Q/tap limits from data file")

        # Arrays intentionally use node/branch IDs directly (1-based, as in Pascal).
        size = max(self.nuz + 2, 36)
        self.p = np.zeros(size, dtype=float)
        self.q = np.zeros(size, dtype=float)
        self.u = np.full(size, 138.0, dtype=float)
        self.d = np.zeros(size, dtype=float)
        self.u_nominal = np.full(size, 138.0, dtype=float)
        self.bsh = np.zeros(size, dtype=float)
        self.vt = np.zeros(size, dtype=int)
        self.ib = np.zeros(self.mvt + 1, dtype=int)
        self.io = np.zeros(self.mvt + 1, dtype=int)
        self.r = np.zeros(self.mvt + 1, dtype=float)
        self.x = np.zeros(self.mvt + 1, dtype=float)
        self.at1 = np.ones(self.mvt + 1, dtype=float)
        self.at2 = np.zeros(self.mvt + 1, dtype=float)
        self.bl = np.zeros(self.mvt + 1, dtype=float)
        self.bt = np.zeros(self.mvt + 1, dtype=int)

        for k, row in enumerate(branch_rows, start=1):
            i, j = int(row[0]), int(row[1])
            if not (1 <= i <= self.nuz + 1 and 1 <= j <= self.nuz + 1):
                raise ValueError(f"Branch {k} has out-of-range bus ID {i}-{j}")
            self.ib[k], self.io[k] = i, j
            self.r[k], self.x[k] = row[2], row[3]
            self.at1[k], self.at2[k] = row[4], row[5]
            self.bl[k], self.bt[k] = row[6], int(row[7])

        controllable = []
        for row in bus_rows:
            i = int(row[0])
            self.p[i], self.q[i], self.u[i] = row[1], row[2], row[3]
            self.d[i], self.bsh[i], self.vt[i] = row[4], row[5], int(row[6])
            self.u_nominal[i] = row[3] if row[3] > 0 else 138.0
            if self.vt[i] != 0:
                controllable.append(i)
        self.u[self.nuz + 1] = self.ubu
        self.d[self.nuz + 1] = self.dbu
        self.u_nominal[self.nuz + 1] = self.ubu

        self.qb = len(controllable)
        self.nuf = np.zeros(self.qb + 1, dtype=int)
        self.qmin = np.zeros(self.qb + 1, dtype=float)
        self.qmax = np.zeros(self.qb + 1, dtype=float)
        for idx, bus in enumerate(controllable, start=1):
            self.nuf[idx] = bus
            self.qmin[idx], self.qmax[idx] = q_bounds
        self.kre_min, self.kre_max, self.kim_min, self.kim_max = tap_bounds
        self._loaded = True

    def form_y_matrix(self) -> None:
        """Build the bus admittance matrix using the source Pascal convention."""
        if not self._loaded:
            raise RuntimeError("Call read_data() before form_y_matrix()")
        n = self.nuz + 1  # includes the slack bus
        Y = np.zeros((n + 1, n + 1), dtype=complex)  # use direct 1-based IDs
        for i in range(1, n + 1):
            Y[i, i] += 1j * self.bsh[i]
        for k in range(1, self.mvt + 1):
            i, j = int(self.ib[k]), int(self.io[k])
            z = complex(self.r[k], self.x[k])
            if abs(z) < 1e-14:
                raise ValueError(f"Branch {k} has zero impedance")
            y = 1.0 / z
            tap = complex(self.at1[k], self.at2[k])
            # Branch charging susceptance is split equally between endpoints.
            ysh = 1j * self.bl[k] / 2.0
            Y[i, i] += y + ysh
            Y[j, j] += (abs(tap) ** 2) * y + ysh
            Y[i, j] -= y * tap
            Y[j, i] -= y * np.conjugate(tap)
        self.Y = Y

    def _state_vector(self) -> np.ndarray:
        buses = list(range(1, self.nuz + 1))
        return np.concatenate([self.d[buses], self.u[buses]])

    def _set_state_vector(self, x: np.ndarray) -> None:
        n = self.nuz
        self.d[1:n + 1] = x[:n]
        self.u[1:n + 1] = x[n:]
        self.u[self.nuz + 1] = self.ubu
        self.d[self.nuz + 1] = self.dbu

    def _calc_injections(self) -> np.ndarray:
        buses = self.nuz + 1
        V = np.zeros(buses + 1, dtype=complex)
        for i in range(1, buses + 1):
            V[i] = self.u[i] * np.exp(1j * self.d[i])
        I = self.Y[1:buses + 1, 1:buses + 1] @ V[1:buses + 1]
        S = V[1:buses + 1] * np.conjugate(I)
        out = np.zeros((buses + 1, 2), dtype=float)
        out[1:, 0] = S.real
        out[1:, 1] = S.imag
        return out

    def _mismatch(self, state: np.ndarray) -> np.ndarray:
        self._set_state_vector(state)
        inj = self._calc_injections()
        # The source data uses positive P/Q for load and negative values for generation.
        p_spec = -self.p[1:self.nuz + 1]
        q_spec = -self.q[1:self.nuz + 1]
        return np.concatenate([inj[1:self.nuz + 1, 0] - p_spec,
                               inj[1:self.nuz + 1, 1] - q_spec])

    def calculate_power_system_regime(self, silent: bool = False,
                                      max_iterations: int = 80) -> bool:
        """Solve the PQ-bus load flow; returns False if Newton iteration fails."""
        if not hasattr(self, "Y"):
            self.form_y_matrix()
        n = self.nuz
        state = self._state_vector()
        # Guard against invalid starting voltages.
        state[n:] = np.where(state[n:] > 1.0, state[n:], 138.0)
        converged = False
        for iteration in range(max_iterations):
            try:
                f = self._mismatch(state)
                if not np.all(np.isfinite(f)):
                    break
                if np.max(np.abs(f)) <= max(self.eps, 1e-7):
                    converged = True
                    break
                m = len(state)
                J = np.empty((m, m), dtype=float)
                for col in range(m):
                    step = 1e-6 if col < n else 1e-4
                    perturbed = state.copy()
                    perturbed[col] += step
                    J[:, col] = (self._mismatch(perturbed) - f) / step
                # Restore the unperturbed state after finite-difference evaluations.
                self._set_state_vector(state)
                delta = np.linalg.solve(J, -f)
                if not np.all(np.isfinite(delta)):
                    break
                # Damped Newton step if a full step does not reduce the mismatch.
                old_norm = np.linalg.norm(f, ord=np.inf)
                scale = 1.0
                accepted = False
                for _ in range(12):
                    trial = state + scale * delta
                    if np.any(trial[n:] <= 1.0):
                        scale *= 0.5
                        continue
                    trial_f = self._mismatch(trial)
                    if np.all(np.isfinite(trial_f)) and np.linalg.norm(trial_f, ord=np.inf) < old_norm:
                        state = trial
                        accepted = True
                        break
                    scale *= 0.5
                if not accepted:
                    # A full Newton update can be useful near a flat residual; accept only finite values.
                    trial = state + 0.1 * delta
                    if np.any(trial[n:] <= 1.0) or not np.all(np.isfinite(trial)):
                        break
                    state = trial
            except (np.linalg.LinAlgError, FloatingPointError, ValueError):
                break
        self._set_state_vector(state)
        if not converged:
            final_mis = self._mismatch(state)
            converged = bool(np.all(np.isfinite(final_mis)) and
                             np.max(np.abs(final_mis)) <= max(self.eps, 1e-7))
        self._calculate_losses()
        if not silent:
            print(f"Power-flow converged: {converged}; iterations: {iteration + 1}; "
                  f"max mismatch: {np.max(np.abs(self._mismatch(state))):.6g}")
            print(f"Active power losses: {self.ddp:.6f} MW")
            print(f"Reactive power losses: {self.ddq:.6f} MVAr")
        return converged

    def _calculate_losses(self) -> None:
        self.ddp = 0.0
        self.ddq = 0.0
        for k in range(1, self.mvt + 1):
            i, j = int(self.ib[k]), int(self.io[k])
            Vi = self.u[i] * np.exp(1j * self.d[i])
            Vj = self.u[j] * np.exp(1j * self.d[j])
            tap = complex(self.at1[k], self.at2[k])
            z = complex(self.r[k], self.x[k])
            y = 1.0 / z
            I = (Vi - tap * Vj) * y
            S_from = Vi * np.conjugate(I)
            S_at_tap = tap * Vj * np.conjugate(I)
            loss = S_from - S_at_tap
            self.ddp += float(loss.real)
            self.ddq += float(loss.imag)

    def save_results(self, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write("Power-flow / optimization results\n")
            f.write("Bus  Voltage_kV  Angle_rad  P_load_MW  Q_load_MVAr  V_pu\n")
            for i in range(1, self.nuz + 1):
                vpu = self.u[i] / self.u_nominal[i]
                f.write(f"{i:3d}  {self.u[i]:12.6f}  {self.d[i]:11.7f}  "
                        f"{self.p[i]:11.5f}  {self.q[i]:12.5f}  {vpu:8.5f}\n")
            f.write(f"\nActive power losses (MW): {self.ddp:.8f}\n")
            f.write(f"Reactive power losses (MVAr): {self.ddq:.8f}\n")
