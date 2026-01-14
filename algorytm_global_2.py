import cvxpy as cp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from scipy.optimize import minimize
import argparse
import os

# --- KLASA OBLICZENIOWA ---
class CloudAllocator:
    def __init__(self, total_capacity):
        self.capacity = total_capacity

    # 1. KRYTERIUM SPRAWIEDLIWOŚCI (Jain's Index)
    def calculate_jains_index(self, allocations):
        if len(allocations) == 0: return 0
        total = np.sum(allocations)
        if total <= 1e-9: return 0
        numerator = total ** 2
        denominator = len(allocations) * np.sum(allocations ** 2)
        return numerator / denominator

    # 2. KRYTERIUM CZASOWE (Makespan - Czas wykonania najwolniejszego zadania)
    def calculate_makespan(self, allocations, min_reqs):
        # Zakładamy: Workload ~ min_reqs. 
        # Czas = Workload / Przydzielone Zasoby
        # Unikamy dzielenia przez zero
        safe_allocs = np.maximum(allocations, 1e-9)
        execution_times = min_reqs / safe_allocs
        return np.max(execution_times) # Makespan to czas najwolniejszego

    # 3. KRYTERIUM Z PRACY NAUKOWEJ (Total Utility / Nash Product)
    def calculate_system_utility(self, allocations, min_reqs):
        # Wg pracy Wei et al., i naszego solvera NBS:
        # Maksymalizujemy iloczyn nadwyżek (lub sumę logarytmów).
        # To jest miara "zadowolenia" systemu z punktu widzenia Teorii Gier.
        surplus = allocations - min_reqs
        # Zabezpieczenie logarytmu
        safe_surplus = np.maximum(surplus, 1e-9)
        return np.sum(np.log(safe_surplus))

    def solve_wei_nbs(self, min_reqs):
        n = len(min_reqs)
        if np.sum(min_reqs) > self.capacity: return None
        
        # Próba 1: CVXPY
        try:
            x = cp.Variable(n)
            surplus = x - min_reqs
            objective = cp.Maximize(cp.sum(cp.log(surplus)))
            constraints = [cp.sum(x) <= self.capacity, surplus >= 1e-7]
            prob = cp.Problem(objective, constraints)
            try: prob.solve(solver=cp.ECOS)
            except: prob.solve(solver=cp.SCS, eps=1e-3)
            
            if x.value is not None: return np.maximum(x.value, min_reqs)
        except: pass
        
        # Próba 2: SciPy
        try:
            fun = lambda x: -np.sum(np.log(x - min_reqs + 1e-9))
            cons = [{'type': 'eq', 'fun': lambda x: self.capacity - np.sum(x)}]
            bnds = [(m, self.capacity) for m in min_reqs]
            x0 = min_reqs + (self.capacity - np.sum(min_reqs))/n
            res = minimize(fun, x0, method='SLSQP', bounds=bnds, constraints=cons)
            if res.success: return res.x
        except: pass
        return None

    def solve_proportional_surplus(self, min_reqs):
        total_req = np.sum(min_reqs)
        if total_req > self.capacity: return None
        surplus_cap = self.capacity - total_req
        if surplus_cap < 0: surplus_cap = 0
        if total_req > 0:
            shares = min_reqs / total_req
            return min_reqs + (shares * surplus_cap)
        else:
            return min_reqs + (surplus_cap / len(min_reqs))

# --- SYMULATOR ---
class SimulationExperiment:
    def __init__(self, multiplier, req_min, req_max):
        self.results = []
        self.multiplier = multiplier
        self.req_min = req_min
        self.req_max = req_max

    def run(self, max_users, step, iterations):
        print(f"Start: M={self.multiplier}, Range=[{self.req_min}-{self.req_max}]")
        for n in tqdm(range(10, max_users + 1, step)):
            for _ in range(iterations):
                avg = (self.req_min + self.req_max) / 2
                cap = n * avg * self.multiplier
                reqs = np.random.uniform(self.req_min, self.req_max, n)
                if np.sum(reqs) >= cap: cap = np.sum(reqs) * 1.05
                
                allocator = CloudAllocator(cap)
                
                # Wei
                wei_alloc = allocator.solve_wei_nbs(reqs)
                if wei_alloc is not None:
                    self.record_result(n, 'Wei et al. (NBS)', wei_alloc, reqs, allocator)
                
                # Proportional
                prop_alloc = allocator.solve_proportional_surplus(reqs)
                if prop_alloc is not None:
                    self.record_result(n, 'Proportional', prop_alloc, reqs, allocator)

    def record_result(self, n, method, alloc, reqs, allocator):
        # 1. Fairness
        surplus = alloc - reqs
        surplus[surplus < 0] = 0
        jain = allocator.calculate_jains_index(surplus)
        
        # 2. Time (Makespan)
        makespan = allocator.calculate_makespan(alloc, reqs)
        
        # 3. Utility (Paper's criterion)
        util = allocator.calculate_system_utility(alloc, reqs)
        
        self.results.append({
            'N_Users': n,
            'Method': method,
            'Fairness': jain,
            'Makespan': makespan,
            'Total_Utility': util
        })

    def plot_all(self, base_filename):
        if not self.results: return
        df = pd.DataFrame(self.results)
        
        # Tworzymy 3 wykresy obok siebie (lub jeden pod drugim)
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        
        # Wykres 1: Fairness (To co było)
        sns.lineplot(data=df, x='N_Users', y='Fairness', hue='Method', style='Method', markers=True, ax=axes[0])
        axes[0].set_title('Kryterium 1: Sprawiedliwość (Jain\'s Index)')
        axes[0].set_ylim(0.5, 1.05)
        
        # Wykres 2: Makespan (Czas)
        sns.lineplot(data=df, x='N_Users', y='Makespan', hue='Method', style='Method', markers=True, ax=axes[1])
        axes[1].set_title('Kryterium 2: Czas Wykonania (Makespan)')
        axes[1].set_ylabel('Czas (jednostki znormalizowane)')
        # Tu niższy wynik jest lepszy!
        
        # Wykres 3: Total Utility (Praca Wei)
        sns.lineplot(data=df, x='N_Users', y='Total_Utility', hue='Method', style='Method', markers=True, ax=axes[2])
        axes[2].set_title('Kryterium 3: Globalna Użyteczność (Wei et al.)')
        axes[2].set_ylabel('Suma Logarytmów Nadwyżki')
        
        plt.tight_layout()
        path = os.path.join('results', 'full_metrics_' + base_filename)
        print(f"Zapisywanie: {path}")
        plt.savefig(path, dpi=300)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--multiplier', type=float, default=1.5)
    parser.add_argument('--min_req', type=float, default=1.0)
    parser.add_argument('--max_req', type=float, default=100.0)
    parser.add_argument('--users', type=int, default=60)
    parser.add_argument('--iter', type=int, default=15)
    args = parser.parse_args()

    fname = f"M{args.multiplier}_R{int(args.min_req)}-{int(args.max_req)}.png"
    sim = SimulationExperiment(args.multiplier, args.min_req, args.max_req)
    sim.run(args.users, 10, args.iter)
    sim.plot_all(fname)