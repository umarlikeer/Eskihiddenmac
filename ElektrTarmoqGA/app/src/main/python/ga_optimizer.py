"""
Power System GA Optimizer

Integrates the genetic algorithm with the power system optimizer,
treating the power flow solver as a black box.

This module:
- Maps chromosomes to power system variables (Q and tap ratios)
- Evaluates fitness by running power flow and computing penalized losses
- Handles constraint violations via penalty functions
"""

import numpy as np
import time
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass

from ga_core import GeneticAlgorithm, GAConfig
from opt_q import PowerSystemOptimizer


@dataclass
class OptimizationResult:
    """Results from GA optimization."""
    best_chromosome: np.ndarray
    best_fitness: float
    final_losses: float
    final_q_values: Dict[int, float]
    final_tap_values: Dict[int, Tuple[float, float]]
    voltage_violations: List[Tuple[int, float]]
    history: List[dict]
    converged: bool
    generations_run: int


class PowerSystemGA:
    """
    Genetic Algorithm optimizer for power system.
    
    Optimizes:
    - Reactive power (Q) at controllable buses
    - Transformer tap ratios (Kre, Kim) at controllable branches
    
    Objective: Minimize total active power losses
    Constraints: Voltage limits (0.95-1.05 p.u.), Q limits, tap limits
    """
    
    # Voltage limits (p.u.)
    V_MIN = 0.95
    V_MAX = 1.05
    # Small numerical tolerance for the iterative load-flow solution (p.u.).
    VOLTAGE_TOLERANCE = 1e-4
    
    # Penalty weight for constraint violations
    VOLTAGE_PENALTY_WEIGHT = 100000000.0
    
    def __init__(
        self,
        data_file: str,
        ga_config: Optional[GAConfig] = None,
        optimize_q: bool = True,
        optimize_taps: bool = True,
        verbose: bool = True
    ):
        """
        Initialize the power system GA optimizer.
        
        Args:
            data_file: Path to the DATA_Q.txt file
            ga_config: GA configuration (uses defaults if None)
            optimize_q: Whether to optimize reactive power
            optimize_taps: Whether to optimize transformer taps
            verbose: Print progress information
        """
        self.data_file = data_file
        self.config = ga_config or GAConfig()
        self.optimize_q = optimize_q
        self.optimize_taps = optimize_taps
        self.verbose = verbose
        
        # Initialize power system from data file
        self._init_power_system()
        
        # Build chromosome structure
        self._build_chromosome_structure()
        
        # Initialize GA
        self.ga = GeneticAlgorithm(self.config)
        
    def _init_power_system(self):
        """Initialize power system and read data."""
        self.pso = PowerSystemOptimizer()
        self.pso.read_data(self.data_file)
        self.pso.form_y_matrix()
        
        # Store initial values
        self.initial_q = self.pso.q.copy()
        self.initial_at1 = self.pso.at1.copy()
        self.initial_at2 = self.pso.at2.copy()
        
    def _build_chromosome_structure(self):
        """
        Build the chromosome structure based on controllable variables.
        
        Chromosome layout:
        [Q_1, Q_2, ..., Q_n, Kre_1, Kim_1, Kre_2, Kim_2, ...]
        """
        self.q_indices = []  # Bus indices with controllable Q
        self.tap_indices = []  # Branch indices with controllable taps
        
        # Find controllable Q buses
        if self.optimize_q:
            for i in range(1, self.pso.qb + 1):
                bus_idx = int(self.pso.nuf[i])
                self.q_indices.append((i, bus_idx))  # (q_array_idx, bus_idx)
        
        # Find controllable transformer branches
        if self.optimize_taps:
            for k in range(1, self.pso.mvt + 1):
                if int(self.pso.bt[k]) == 1:
                    self.tap_indices.append(k)
        
        # Calculate chromosome dimensions
        self.n_q_vars = len(self.q_indices)
        self.n_tap_vars = len(self.tap_indices) * 2  # Kre and Kim for each
        self.n_vars = self.n_q_vars + self.n_tap_vars
        
        # Build bounds array
        self._build_bounds()
        
        if self.verbose:
            print(f"Chromosome structure:")
            print(f"  Q variables: {self.n_q_vars} (buses: {[b for _, b in self.q_indices]})")
            print(f"  Tap variables: {self.n_tap_vars} (branches: {self.tap_indices})")
            print(f"  Total variables: {self.n_vars}")
    
    def _build_bounds(self):
        """Build the bounds array for all decision variables."""
        bounds = []
        
        # Q bounds
        for i, bus_idx in self.q_indices:
            q_min = self.pso.qmin[i]
            q_max = self.pso.qmax[i]
            bounds.append([q_min, q_max])
        
        # Tap bounds (Kre, Kim pairs)
        for k in self.tap_indices:
            bounds.append([self.pso.kre_min, self.pso.kre_max])  # Kre
            bounds.append([self.pso.kim_min, self.pso.kim_max])  # Kim
        
        self.bounds = np.array(bounds)
    
    def decode_chromosome(self, chromosome: np.ndarray) -> None:
        """
        Decode chromosome and update power system variables.
        
        Args:
            chromosome: Array of decision variable values
        """
        idx = 0
        
        # Decode Q values
        for i, bus_idx in self.q_indices:
            self.pso.q[bus_idx] = chromosome[idx]
            idx += 1
        
        # Decode tap values
        for k in self.tap_indices:
            self.pso.at1[k] = chromosome[idx]  # Kre
            self.pso.at2[k] = chromosome[idx + 1]  # Kim
            idx += 2
        
        # Reform Y matrix with new tap values
        if self.optimize_taps:
            self.pso.form_y_matrix()
    
    def evaluate_fitness(self, chromosome: np.ndarray) -> float:
        """
        Evaluate fitness of a chromosome.
        
        Runs power flow and returns penalized active power losses.
        
        Args:
            chromosome: Decision variable values
            
        Returns:
            Fitness value (lower is better)
        """
        # Reset every candidate to the same original operating point.  The
        # network's own nominal bus voltages are used (138 kV here), not 220 kV.
        self.pso.q = self.initial_q.copy()
        self.pso.at1 = self.initial_at1.copy()
        self.pso.at2 = self.initial_at2.copy()
        self.pso.u = self.pso.u_nominal.copy()
        self.pso.d = np.zeros_like(self.pso.d)
        self.pso.u[self.pso.nuz + 1] = self.pso.ubu
        self.pso.d[self.pso.nuz + 1] = self.pso.dbu

        # Apply chromosome and solve power flow (silent mode).
        try:
            self.decode_chromosome(chromosome)
            converged = self.pso.calculate_power_system_regime(
                silent=True, max_iterations=80
            )
            if not converged:
                return 1e10  # Penalty for non-convergence
        except Exception:
            return 1e10
        
        # Get active power losses
        losses = self.pso.ddp
        
        # Calculate voltage violation penalty
        penalty = self._calculate_voltage_penalty()
        
        return losses + penalty
    
    def _calculate_voltage_penalty(self) -> float:
        """
        Calculate penalty for voltage limit violations.
        
        Returns:
            Penalty value
        """
        penalty = 0.0
        
        for i in range(1, self.pso.nuz + 1):
            v = self.pso.u[i]
            
            # Normalize against the nominal voltage specified for this bus.
            v_base = float(self.pso.u_nominal[i])
            v_pu = v / v_base if v_base > 0 else float("inf")
            
            # Check violations
            if v_pu > self.V_MAX:
                excess = v_pu - self.V_MAX
                penalty += self.VOLTAGE_PENALTY_WEIGHT * excess ** 2
            elif v_pu < self.V_MIN:
                excess = self.V_MIN - v_pu
                penalty += self.VOLTAGE_PENALTY_WEIGHT * excess ** 2
        
        return penalty
    
    def get_voltage_violations(self) -> List[Tuple[int, float]]:
        """
        Get list of voltage violations.
        
        Returns:
            List of (bus_index, voltage_pu) for violated buses
        """
        violations = []
        
        for i in range(1, self.pso.nuz + 1):
            v_base = float(self.pso.u_nominal[i])
            v_pu = self.pso.u[i] / v_base if v_base > 0 else float("inf")
            
            if (v_pu > self.V_MAX + self.VOLTAGE_TOLERANCE or
                    v_pu < self.V_MIN - self.VOLTAGE_TOLERANCE):
                violations.append((i, v_pu))
        
        return violations
    
    def run(self) -> OptimizationResult:
        """
        Run the GA optimization.
        
        Returns:
            OptimizationResult with best solution and statistics
        """
        if self.n_vars == 0:
            raise ValueError("No decision variables specified. "
                           "Enable optimize_q or optimize_taps.")
        
        if self.verbose:
            print("\n" + "="*60)
            print("Starting GA Optimization")
            print("="*60)
            print(f"Population size: {self.config.population_size}")
            print(f"Max generations: {self.config.max_generations}")
            print(f"Crossover prob: {self.config.crossover_prob}")
            print(f"Mutation prob: {self.config.mutation_prob}")
            print("="*60 + "\n")
        
        # Run GA
        best_chromosome, best_fitness, history = self.ga.optimize(
            fitness_func=self.evaluate_fitness,
            bounds=self.bounds,
            verbose=self.verbose
        )
        
        if not np.isfinite(best_fitness) or best_fitness >= 1e10:
            raise RuntimeError(
                "No feasible chromosome produced a converged power-flow solution. "
                "Check the input data, bounds, and power-flow model."
            )

        # Re-evaluate the best candidate from the same nominal initial state.
        self.pso.q = self.initial_q.copy()
        self.pso.at1 = self.initial_at1.copy()
        self.pso.at2 = self.initial_at2.copy()
        self.pso.u = self.pso.u_nominal.copy()
        self.pso.d = np.zeros_like(self.pso.d)
        self.pso.u[self.pso.nuz + 1] = self.pso.ubu
        self.pso.d[self.pso.nuz + 1] = self.pso.dbu
        self.decode_chromosome(best_chromosome)
        final_converged = self.pso.calculate_power_system_regime(
            silent=True, max_iterations=80
        )
        if not final_converged:
            raise RuntimeError("The best chromosome did not converge on final verification.")
        
        # Collect results
        final_q = {}
        for i, bus_idx in self.q_indices:
            final_q[bus_idx] = self.pso.q[bus_idx]
        
        final_taps = {}
        for k in self.tap_indices:
            final_taps[k] = (self.pso.at1[k], self.pso.at2[k])
        
        violations = self.get_voltage_violations()
        
        return OptimizationResult(
            best_chromosome=best_chromosome,
            best_fitness=best_fitness,
            final_losses=self.pso.ddp,
            final_q_values=final_q,
            final_tap_values=final_taps,
            voltage_violations=violations,
            history=history,
            converged=len(history) < self.config.max_generations,
            generations_run=len(history)
        )
    
    def print_results(self, result: OptimizationResult) -> None:
        """Print optimization results in a formatted way."""
        print("\n" + "="*60)
        print("OPTIMIZATION RESULTS")
        print("="*60)
        
        print(f"\nGenerations run: {result.generations_run}")
        print(f"Converged: {'Yes' if result.converged else 'No'}")
        
        print(f"\nFinal active power losses: {result.final_losses:.6f} MW")
        print(f"Best fitness (with penalties): {result.best_fitness:.6f}")
        
        if result.final_q_values:
            print("\nOptimized Q values (MVAr):")
            for bus_idx, q_val in result.final_q_values.items():
                print(f"  Bus {bus_idx}: {q_val:.4f}")
        
        if result.final_tap_values:
            print("\nOptimized Transformer Taps:")
            for branch_idx, (kre, kim) in result.final_tap_values.items():
                i, j = int(self.pso.ib[branch_idx]), int(self.pso.io[branch_idx])
                print(f"  Branch {i}-{j}: Kre={kre:.4f}, Kim={kim:.4f}")
        
        print("\nBus voltages (p.u.):")
        for i in range(1, self.pso.nuz + 1):
            v_base = float(self.pso.u_nominal[i])
            v_pu = self.pso.u[i] / v_base if v_base > 0 else float("inf")
            status = ""
            if v_pu > self.V_MAX + self.VOLTAGE_TOLERANCE:
                status = " [HIGH]"
            elif v_pu < self.V_MIN - self.VOLTAGE_TOLERANCE:
                status = " [LOW]"
            print(f"  Bus {i}: {v_pu:.4f}{status}")
        
        if result.voltage_violations:
            print(f"\nVoltage violations: {len(result.voltage_violations)}")
            for bus_idx, v_pu in result.voltage_violations:
                print(f"  Bus {bus_idx}: {v_pu:.4f} p.u.")
        else:
            print("\nNo voltage violations!")
        
        print("="*60)


if __name__ == "__main__":
    import os
    
    # Test with DATA_Q14.txt
    data_path = os.path.join(os.path.dirname(__file__), 'DATA_Q14.txt')
    
    config = GAConfig(
        population_size=30,
        max_generations=30,
        crossover_prob=0.9,
        mutation_prob=0.15
    )
    
    optimizer = PowerSystemGA(
        data_file=data_path,
        ga_config=config,
        optimize_q=True,
        optimize_taps=True,
        verbose=True
    )
    
    result = optimizer.run()
    optimizer.print_results(result)
