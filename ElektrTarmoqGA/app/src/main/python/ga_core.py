"""
Real-Coded Genetic Algorithm Core Module

Contains pure GA operators independent of any specific optimization problem.
Designed for bounded real-valued optimization.

Operators:
- Tournament Selection
- Simulated Binary Crossover (SBX)
- Polynomial Mutation (adaptive)
- Constraint repair (clipping)
"""

import numpy as np
from typing import Tuple, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class GAConfig:
    """Configuration for Genetic Algorithm parameters."""
    population_size: int = 50
    max_generations: int = 100
    crossover_prob: float = 0.9
    mutation_prob: float = 0.1
    tournament_size: int = 3
    eta_c: float = 15.0  # SBX distribution index
    eta_m_initial: float = 20.0  # Initial mutation distribution index
    eta_m_final: float = 100.0  # Final mutation distribution index (for fine-tuning)
    elitism_count: int = 2
    convergence_threshold: float = 1e-6
    convergence_generations: int = 10


class GeneticAlgorithm:
    """
    Real-coded Genetic Algorithm implementation.
    
    Features:
    - Tournament selection with configurable pressure
    - Simulated Binary Crossover (SBX)
    - Adaptive Polynomial Mutation
    - Elitism preservation
    - Convergence detection
    """
    
    def __init__(self, config: Optional[GAConfig] = None):
        self.config = config or GAConfig()
        self.rng = np.random.default_rng()
        
    def initialize_population(
        self, 
        bounds: np.ndarray,
        size: Optional[int] = None
    ) -> np.ndarray:
        """
        Initialize random population within bounds.
        
        Args:
            bounds: Array of shape (n_vars, 2) with [min, max] for each variable
            size: Population size (uses config if not specified)
            
        Returns:
            Population array of shape (pop_size, n_vars)
        """
        pop_size = size or self.config.population_size
        n_vars = len(bounds)
        
        population = np.zeros((pop_size, n_vars))
        for i in range(n_vars):
            population[:, i] = self.rng.uniform(
                bounds[i, 0], bounds[i, 1], pop_size
            )
        return population
    
    def tournament_select(
        self,
        population: np.ndarray,
        fitness: np.ndarray,
        k: Optional[int] = None
    ) -> np.ndarray:
        """
        Tournament selection (minimization assumed).
        
        Args:
            population: Current population
            fitness: Fitness values (lower is better)
            k: Tournament size
            
        Returns:
            Selected individual
        """
        pop_size = len(population)
        k = self.config.tournament_size if k is None else k
        k = max(1, min(int(k), pop_size))
        
        # Random tournament participants
        indices = self.rng.choice(pop_size, size=k, replace=False)
        
        # Select winner (minimum fitness)
        winner_idx = indices[np.argmin(fitness[indices])]
        return population[winner_idx].copy()
    
    def sbx_crossover(
        self,
        parent1: np.ndarray,
        parent2: np.ndarray,
        bounds: np.ndarray,
        eta_c: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulated Binary Crossover (SBX).
        
        Produces two offspring from two parents using polynomial
        probability distribution that simulates single-point crossover
        in binary representation.
        
        Args:
            parent1, parent2: Parent individuals
            bounds: Variable bounds (n_vars, 2)
            eta_c: Distribution index (higher = children closer to parents)
            
        Returns:
            Tuple of two offspring
        """
        eta_c = self.config.eta_c if eta_c is None else eta_c
        n_vars = len(parent1)
        
        child1 = parent1.copy()
        child2 = parent2.copy()
        
        for i in range(n_vars):
            if self.rng.random() > 0.5:
                continue
                
            if abs(parent1[i] - parent2[i]) < 1e-14:
                continue
            
            y1 = min(parent1[i], parent2[i])
            y2 = max(parent1[i], parent2[i])
            
            lb = bounds[i, 0]
            ub = bounds[i, 1]
            
            # Calculate beta for child 1
            beta1 = 1.0 + (2.0 * (y1 - lb) / (y2 - y1 + 1e-14))
            alpha1 = 2.0 - beta1 ** (-(eta_c + 1))
            
            # Calculate beta for child 2
            beta2 = 1.0 + (2.0 * (ub - y2) / (y2 - y1 + 1e-14))
            alpha2 = 2.0 - beta2 ** (-(eta_c + 1))
            
            u = self.rng.random()
            
            # Calculate betaq for child 1
            if u <= 1.0 / alpha1:
                betaq1 = (u * alpha1) ** (1.0 / (eta_c + 1))
            else:
                betaq1 = (1.0 / (2.0 - u * alpha1)) ** (1.0 / (eta_c + 1))
            
            # Calculate betaq for child 2
            u = self.rng.random()
            if u <= 1.0 / alpha2:
                betaq2 = (u * alpha2) ** (1.0 / (eta_c + 1))
            else:
                betaq2 = (1.0 / (2.0 - u * alpha2)) ** (1.0 / (eta_c + 1))
            
            # Generate children
            c1 = 0.5 * ((y1 + y2) - betaq1 * (y2 - y1))
            c2 = 0.5 * ((y1 + y2) + betaq2 * (y2 - y1))
            
            # Ensure within bounds
            child1[i] = np.clip(c1, lb, ub)
            child2[i] = np.clip(c2, lb, ub)
        
        return child1, child2
    
    def polynomial_mutation(
        self,
        individual: np.ndarray,
        bounds: np.ndarray,
        eta_m: Optional[float] = None,
        prob: Optional[float] = None
    ) -> np.ndarray:
        """
        Polynomial mutation operator.
        
        Args:
            individual: Individual to mutate
            bounds: Variable bounds (n_vars, 2)
            eta_m: Distribution index (higher = smaller mutations)
            prob: Mutation probability per gene
            
        Returns:
            Mutated individual
        """
        eta_m = self.config.eta_m_initial if eta_m is None else eta_m
        prob = self.config.mutation_prob if prob is None else prob
        
        mutant = individual.copy()
        n_vars = len(individual)
        
        for i in range(n_vars):
            if self.rng.random() >= prob:
                continue
            
            y = individual[i]
            lb = bounds[i, 0]
            ub = bounds[i, 1]
            delta = ub - lb
            
            if delta < 1e-14:
                continue
            
            u = self.rng.random()
            
            if u < 0.5:
                delta_l = (y - lb) / delta
                deltaq = (2.0 * u + (1 - 2.0 * u) * (1 - delta_l) ** (eta_m + 1)) ** (1.0 / (eta_m + 1)) - 1.0
            else:
                delta_r = (ub - y) / delta
                deltaq = 1.0 - (2.0 * (1 - u) + 2.0 * (u - 0.5) * (1 - delta_r) ** (eta_m + 1)) ** (1.0 / (eta_m + 1))
            
            mutant[i] = np.clip(y + deltaq * delta, lb, ub)
        
        return mutant
    
    def repair(
        self,
        individual: np.ndarray,
        bounds: np.ndarray
    ) -> np.ndarray:
        """
        Repair individual by clipping to bounds.
        
        Args:
            individual: Individual to repair
            bounds: Variable bounds (n_vars, 2)
            
        Returns:
            Repaired individual
        """
        repaired = individual.copy()
        for i in range(len(individual)):
            repaired[i] = np.clip(individual[i], bounds[i, 0], bounds[i, 1])
        return repaired
    
    def get_adaptive_eta_m(self, generation: int, max_generation: int) -> float:
        """
        Calculate adaptive mutation distribution index.
        
        Starts with eta_m_initial (more exploration) and
        increases to eta_m_final (more exploitation) as
        generations progress.
        
        Args:
            generation: Current generation number
            max_generation: Maximum number of generations
            
        Returns:
            Current eta_m value
        """
        progress = generation / max(1, max_generation - 1)
        return self.config.eta_m_initial + progress * (
            self.config.eta_m_final - self.config.eta_m_initial
        )
    
    def check_convergence(
        self,
        fitness_history: List[float],
        threshold: Optional[float] = None,
        generations: Optional[int] = None
    ) -> bool:
        """
        Check if the algorithm has converged.
        
        Convergence is detected if the best fitness hasn't
        improved significantly over the specified number of generations.
        
        Args:
            fitness_history: List of best fitness values per generation
            threshold: Minimum improvement to consider as progress
            generations: Number of generations to check
            
        Returns:
            True if converged
        """
        threshold = threshold or self.config.convergence_threshold
        generations = generations or self.config.convergence_generations
        
        if len(fitness_history) < generations:
            return False
        
        recent = fitness_history[-generations:]
        improvement = max(recent) - min(recent)
        
        return improvement < threshold
    
    def evolve_population(
        self,
        population: np.ndarray,
        fitness: np.ndarray,
        bounds: np.ndarray,
        generation: int
    ) -> np.ndarray:
        """
        Create next generation through selection, crossover, and mutation.
        
        Args:
            population: Current population
            fitness: Fitness values
            bounds: Variable bounds
            generation: Current generation number
            
        Returns:
            New population
        """
        pop_size = len(population)
        new_population = []
        
        # Elitism: preserve best individuals
        elite_indices = np.argsort(fitness)[:self.config.elitism_count]
        for idx in elite_indices:
            new_population.append(population[idx].copy())
        
        # Adaptive mutation parameter
        eta_m = self.get_adaptive_eta_m(generation, self.config.max_generations)
        
        # Generate remaining offspring
        while len(new_population) < pop_size:
            # Selection
            parent1 = self.tournament_select(population, fitness)
            parent2 = self.tournament_select(population, fitness)
            
            # Crossover
            if self.rng.random() < self.config.crossover_prob:
                child1, child2 = self.sbx_crossover(parent1, parent2, bounds)
            else:
                child1, child2 = parent1.copy(), parent2.copy()
            
            # Mutation
            child1 = self.polynomial_mutation(child1, bounds, eta_m)
            child2 = self.polynomial_mutation(child2, bounds, eta_m)
            
            # Repair (ensure bounds)
            child1 = self.repair(child1, bounds)
            child2 = self.repair(child2, bounds)
            
            new_population.append(child1)
            if len(new_population) < pop_size:
                new_population.append(child2)
        
        return np.array(new_population[:pop_size])
    
    def optimize(
        self,
        fitness_func: Callable[[np.ndarray], float],
        bounds: np.ndarray,
        verbose: bool = True
    ) -> Tuple[np.ndarray, float, List[dict]]:
        """
        Run the genetic algorithm optimization.
        
        Args:
            fitness_func: Function that takes an individual and returns fitness (lower is better)
            bounds: Variable bounds of shape (n_vars, 2)
            verbose: Print progress information
            
        Returns:
            Tuple of (best_individual, best_fitness, history)
        """
        import time
        
        # Initialize
        population = self.initialize_population(bounds)
        
        if verbose:
            print("Initializing population...")
        
        fitness = np.array([fitness_func(ind) for ind in population])
        
        best_idx = np.argmin(fitness)
        best_individual = population[best_idx].copy()
        best_fitness = fitness[best_idx]
        
        history = []
        fitness_history = [best_fitness]
        
        start_time = time.time()
        
        if verbose:
            print(f"\nStarting GA optimization...")
            print(f"Initial best fitness: {best_fitness:.6f}")
            print("-" * 60)
        
        for gen in range(self.config.max_generations):
            gen_start = time.time()
            
            # Evolve population
            population = self.evolve_population(population, fitness, bounds, gen)
            
            # Evaluate fitness
            fitness = np.array([fitness_func(ind) for ind in population])
            
            # Update best
            gen_best_idx = np.argmin(fitness)
            if fitness[gen_best_idx] < best_fitness:
                best_fitness = fitness[gen_best_idx]
                best_individual = population[gen_best_idx].copy()
            
            # Record history
            gen_info = {
                'generation': gen + 1,
                'best_fitness': best_fitness,
                'mean_fitness': np.mean(fitness),
                'std_fitness': np.std(fitness),
                'eta_m': self.get_adaptive_eta_m(gen, self.config.max_generations)
            }
            history.append(gen_info)
            fitness_history.append(best_fitness)
            
            if verbose:
                gen_time = time.time() - gen_start
                elapsed = time.time() - start_time
                remaining = (self.config.max_generations - gen - 1) * (elapsed / (gen + 1))
                
                # Progress bar
                progress = (gen + 1) / self.config.max_generations
                bar_length = 30
                filled = int(bar_length * progress)
                bar = "#" * filled + "-" * (bar_length - filled)
                
                print(f"\r[{bar}] Gen {gen+1:3d}/{self.config.max_generations} | "
                      f"Best: {best_fitness:.4f} | Mean: {gen_info['mean_fitness']:.4f} | "
                      f"ETA: {remaining:.0f}s", end="", flush=True)
            
            # Check convergence
            if self.check_convergence(fitness_history):
                if verbose:
                    print(f"\n\n[OK] Converged at generation {gen + 1}!")
                break
        
        if verbose:
            total_time = time.time() - start_time
            print(f"\n\nOptimization completed in {total_time:.1f} seconds")
            print(f"Final best fitness: {best_fitness:.6f}")
        
        return best_individual, best_fitness, history


if __name__ == "__main__":
    # Quick test with Rastrigin function
    def rastrigin(x):
        return 10 * len(x) + sum(xi**2 - 10 * np.cos(2 * np.pi * xi) for xi in x)
    
    config = GAConfig(
        population_size=30,
        max_generations=50,
        crossover_prob=0.9,
        mutation_prob=0.1
    )
    
    ga = GeneticAlgorithm(config)
    bounds = np.array([[-5.12, 5.12]] * 5)  # 5-dimensional Rastrigin
    
    best, best_fit, history = ga.optimize(rastrigin, bounds)
    print(f"\nBest solution: {best}")
    print(f"Best fitness: {best_fit}")
