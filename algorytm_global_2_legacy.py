import cvxpy as cp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from scipy.optimize import minimize
import argparse 
import os

# -----------------------------------------------------------------------------
# CZĘŚĆ 1: SILNIK OBLICZENIOWY 
# -----------------------------------------------------------------------------
class CloudAllocator:
    def __init__(self, total_capacity):
        self.capacity = total_capacity

    def calculate_jains_index(self, allocations):
        if len(allocations) == 0: return 0
        total = np.sum(allocations)
        if total <= 1e-9: return 0
        numerator = total ** 2
        denominator = len(allocations) * np.sum(allocations ** 2)
        return numerator / denominator if denominator != 0 else 0

    def solve_wei_nbs(self, min_reqs):
        n = len(min_reqs)
        total_min = np.sum(min_reqs)
        
        if total_min > self.capacity: return None

        # --- PRÓBA 1 & 2: CVXPY ---
        try:
            x = cp.Variable(n)
            surplus = x - min_reqs
            objective = cp.Maximize(cp.sum(cp.log(surplus)))
            constraints = [cp.sum(x) <= self.capacity, surplus >= 1e-7]
            problem = cp.Problem(objective, constraints)
            
            try:
                problem.solve(solver=cp.ECOS)
            except:
                problem.solve(solver=cp.SCS, eps=1e-3)

            if x.value is not None:
                return np.maximum(x.value, min_reqs)
        except Exception:
            pass 

        # --- PRÓBA 3: SciPy ---
        def objective_func(x):
            s = x - min_reqs
            if np.any(s <= 1e-9): return 1e9 
            return -np.sum(np.log(s))

        constraints_scipy = [{'type': 'eq', 'fun': lambda x: self.capacity - np.sum(x)}]
        bounds = [(m + 1e-7, self.capacity) for m in min_reqs]
        surplus_available = self.capacity - total_min
        x0 = min_reqs + (surplus_available / n)
        
        try:
            result = minimize(objective_func, x0, method='SLSQP', bounds=bounds, constraints=constraints_scipy)
            if result.success: return result.x
        except:
            return None
        return None

    def solve_proportional_surplus(self, min_reqs):
        total_req = np.sum(min_reqs)
        if total_req > self.capacity: return None
        surplus_capacity = self.capacity - total_req
        if surplus_capacity < 0: surplus_capacity = 0
        if total_req > 0:
            shares = min_reqs / total_req 
            surplus_allocation = shares * surplus_capacity
        else:
            surplus_allocation = np.full(len(min_reqs), surplus_capacity / len(min_reqs))
        return min_reqs + surplus_allocation

# -----------------------------------------------------------------------------
# CZĘŚĆ 2: SYMULATOR Z PARAMETRAMI
# -----------------------------------------------------------------------------
class SimulationExperiment:
    def __init__(self, multiplier, req_min, req_max):
        self.results = []
        self.multiplier = multiplier  # Mnożnik capacity (1.1 = bieda, 1.5 = norma)
        self.req_min = req_min        # Min. zakres losowania
        self.req_max = req_max        # Max. zakres losowania

    def run_scaling_experiment(self, max_users, step, iterations):
        print(f"--- START SYMULACJI ---")
        print(f"Parametry: Multiplier={self.multiplier}, Range=[{self.req_min}, {self.req_max}], MaxUsers={max_users}")
        
        for n_users in tqdm(range(10, max_users + 1, step)):
            for _ in range(iterations):
                # Generowanie środowiska wg parametrów
                avg_req = (self.req_min + self.req_max) / 2
                
                # Używamy parametru multiplier do ustalenia "tłoku"
                capacity = n_users * avg_req * self.multiplier
                
                # Używamy parametrów req_min/max do ustalenia heterogeniczności
                min_reqs = np.random.uniform(self.req_min, self.req_max, n_users)
                
                total_min = np.sum(min_reqs)
                if total_min >= capacity:
                    capacity = total_min * 1.05 # Minimalny zapas bezpieczeństwa

                allocator = CloudAllocator(capacity)
                
                # 1. Metoda Wei
                alloc_wei = allocator.solve_wei_nbs(min_reqs)
                if alloc_wei is not None:
                    surplus_wei = alloc_wei - min_reqs
                    surplus_wei[surplus_wei < 0] = 0
                    self.results.append({
                        'N_Users': n_users, 
                        'Method': 'Wei et al. (NBS)', 
                        'Fairness_Index': allocator.calculate_jains_index(surplus_wei)
                    })

                # 2. Metoda Proporcjonalna
                alloc_prop = allocator.solve_proportional_surplus(min_reqs)
                if alloc_prop is not None:
                    surplus_prop = alloc_prop - min_reqs
                    surplus_prop[surplus_prop < 0] = 0
                    self.results.append({
                        'N_Users': n_users, 
                        'Method': 'Proportional Surplus', 
                        'Fairness_Index': allocator.calculate_jains_index(surplus_prop)
                    })

    def plot_results(self, filename):
        if not self.results:
            print("BRAK WYNIKÓW!")
            return

        df = pd.DataFrame(self.results)
        
        sns.set_style("whitegrid")
        plt.figure(figsize=(10, 6))
        
        sns.lineplot(
            data=df, x='N_Users', y='Fairness_Index', 
            hue='Method', style='Method', markers=True, linewidth=2.5
        )
        
        plt.title(f'Fairness Index (Cap={self.multiplier}x, Range={self.req_min}-{self.req_max})', fontsize=14)
        plt.ylabel('Fairness Index (Surplus)', fontsize=12)
        plt.ylim(0.5, 1.05)
        
        # Zapis do dynamicznej nazwy pliku
        path = os.path.join('results', filename)
        print(f"Zapisywanie wykresu do: {path}")
        plt.savefig(path, dpi=300)

if __name__ == "__main__":
    # Konfiguracja parsera argumentów
    parser = argparse.ArgumentParser(description='Symulacja Cloud Resource Allocation')
    
    # Domyślne wartości (takie jak w Scenariuszu A)
    parser.add_argument('--multiplier', type=float, default=1.5, help='Mnożnik zasobów (1.1 = mało, 2.0 = dużo)')
    parser.add_argument('--min_req', type=float, default=5.0, help='Dolna granica wymagań zadania')
    parser.add_argument('--max_req', type=float, default=25.0, help='Górna granica wymagań zadania')
    parser.add_argument('--users', type=int, default=60, help='Maksymalna liczba użytkowników')
    parser.add_argument('--iter', type=int, default=15, help='Liczba powtórzeń na krok')

    args = parser.parse_args()

    # Tworzenie nazwy pliku na podstawie parametrów
    # Np. sim_M1.1_R5-25_N60.png
    output_filename = f"sim_M{args.multiplier}_R{int(args.min_req)}-{int(args.max_req)}_N{args.users}.png"

    sim = SimulationExperiment(args.multiplier, args.min_req, args.max_req)
    sim.run_scaling_experiment(max_users=args.users, step=10, iterations=args.iter)
    sim.plot_results(output_filename)