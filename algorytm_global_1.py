import cvxpy as cp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from scipy.optimize import minimize  # <--- Nowy import (Plan B)

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
        """
        Próbuje rozwiązać problem metodą Wei (NBS).
        Strategia: CVXPY (ECOS) -> CVXPY (SCS) -> SciPy (SLSQP).
        """
        n = len(min_reqs)
        total_min = np.sum(min_reqs)
        
        # 1. Sprawdzenie wykonalności
        if total_min > self.capacity:
            return None

        # --- PRÓBA 1 & 2: CVXPY (Solver matematyczny) ---
        try:
            x = cp.Variable(n)
            surplus = x - min_reqs
            # Używamy sumy logarytmów (odpowiednik iloczynu Nasha)
            objective = cp.Maximize(cp.sum(cp.log(surplus)))
            
            # Ograniczenia
            constraints = [
                cp.sum(x) <= self.capacity,
                surplus >= 1e-7 # Bardzo mały epsilon
            ]
            
            problem = cp.Problem(objective, constraints)
            
            # Najpierw ECOS (szybki)
            try:
                problem.solve(solver=cp.ECOS)
            except:
                # Jak nie wyjdzie, to SCS (stabilny)
                problem.solve(solver=cp.SCS, eps=1e-3)

            if x.value is not None:
                # Zwracamy wynik jeśli jest sensowny
                return np.maximum(x.value, min_reqs)
        
        except Exception as e:
            pass # Ignorujemy błędy CVXPY i idziemy do Planu B

        # --- PRÓBA 3: SciPy (Plan B - "Nuclear Option") ---
        # Jeśli solver dedykowany zawiódł, używamy ogólnego optymalizatora numerycznego.
        # Minimalizujemy funkcję: -sum(log(x - min))
        
        def objective_func(x):
            s = x - min_reqs
            # Kara za naruszenie granicy (żeby logarytm nie wybuchł)
            if np.any(s <= 1e-9): return 1e9 
            return -np.sum(np.log(s))

        # Warunek: suma(x) = capacity (NBS zawsze zużywa całość w tym modelu)
        constraints_scipy = [
            {'type': 'eq', 'fun': lambda x: self.capacity - np.sum(x)}
        ]
        
        # Granice zmiennych: od min_reqs do capacity
        bounds = [(m + 1e-7, self.capacity) for m in min_reqs]
        
        # Punkt startowy: równy podział nadwyżki
        surplus_available = self.capacity - total_min
        x0 = min_reqs + (surplus_available / n)
        
        try:
            result = minimize(
                objective_func, 
                x0, 
                method='SLSQP', 
                bounds=bounds, 
                constraints=constraints_scipy
            )
            if result.success:
                return result.x
        except:
            return None # Jeśli nawet to zawiedzie, to dane są błędne
            
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
# CZĘŚĆ 2: SYMULATOR
# -----------------------------------------------------------------------------
class SimulationExperiment:
    def __init__(self):
        self.results = []

    def run_scaling_experiment(self, max_users=50, step=5, iterations=10):
        print(f"--- ROZPOCZYNAM EKSPERYMENT (N=10..{max_users}) ---")
        
        for n_users in tqdm(range(10, max_users + 1, step)):
            for _ in range(iterations):
                # Generujemy dane
                avg_req = 10
                # Dajemy trochę więcej luzu (1.5x), żeby solvery miały łatwiej na start
                capacity = n_users * avg_req * 1.5 
                min_reqs = np.random.uniform(5, 25, n_users)
                
                # Walidacja danych (żeby capacity zawsze było większe od sumy wymagań)
                total_min = np.sum(min_reqs)
                if total_min >= capacity:
                    capacity = total_min * 1.2 # Zwiększamy chmurę o 20%

                allocator = CloudAllocator(capacity)
                
                # 1. Metoda Wei (NBS)
                alloc_wei = allocator.solve_wei_nbs(min_reqs)
                if alloc_wei is not None:
                    surplus_wei = alloc_wei - min_reqs
                    surplus_wei[surplus_wei < 0] = 0
                    fairness_wei = allocator.calculate_jains_index(surplus_wei)
                    self.results.append({
                        'N_Users': n_users, 
                        'Method': 'Wei et al. (NBS)', 
                        'Fairness_Index': fairness_wei
                    })
                else:
                    # Logujemy błąd, jeśli mimo Planu B się nie udało
                    print(f"\n[Warning] NBS Failed for N={n_users}")

                # 2. Metoda Proporcjonalna
                alloc_prop = allocator.solve_proportional_surplus(min_reqs)
                if alloc_prop is not None:
                    surplus_prop = alloc_prop - min_reqs
                    surplus_prop[surplus_prop < 0] = 0
                    fairness_prop = allocator.calculate_jains_index(surplus_prop)
                    self.results.append({
                        'N_Users': n_users, 
                        'Method': 'Proportional Surplus', 
                        'Fairness_Index': fairness_prop
                    })

    def plot_results(self):
        if not self.results:
            print("CRITICAL ERROR: Brak wyników do wyświetlenia.")
            return None
            
        df = pd.DataFrame(self.results)
        
        # Sprawdzamy czy mamy obie metody
        methods_found = df['Method'].unique()
        print(f"\nZnalezione metody w wynikach: {methods_found}")
        
        sns.set_style("whitegrid")
        plt.figure(figsize=(10, 6))
        
        sns.lineplot(
            data=df, 
            x='N_Users', 
            y='Fairness_Index', 
            hue='Method', 
            style='Method',
            markers=True, 
            linewidth=2.5
        )
        
        plt.title('Porównanie sprawiedliwości alokacji (Jain\'s Index)', fontsize=14)
        plt.ylabel('Fairness Index (dla nadwyżki)', fontsize=12)
        plt.ylim(0.5, 1.05)
        
        print("Zapisywanie wykresu do results/wykres_badania.png ...")
        plt.savefig('results/wykres_badania.png', dpi=300)
        return df

if __name__ == "__main__":
    sim = SimulationExperiment()
    sim.run_scaling_experiment(max_users=60, step=10, iterations=15)
    sim.plot_results()