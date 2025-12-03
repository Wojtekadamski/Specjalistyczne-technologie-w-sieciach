import numpy as np
import copy

class WeiCloudProject:
    # Algorytm alokacji zasobów wg Wei et al. (2010)
    # Obsługuje SPELR i GELR przy multiplexingu
    
    def __init__(self, prices, exec_times, subtasks_count, wt=0.5, we=0.5):
        # dane wejściowe z modelu
        self.PRICES = np.array(prices)
        self.EXEC_TIMES = np.array(exec_times)
        self.SUBTASKS_COUNT = subtasks_count
        self.WT = wt
        self.WE = we                             
        
        self.num_tasks = len(subtasks_count)
        self.num_resources = len(prices)

    def calculate_utility(self, task_idx, strategy_vector, load_vector):
        # oblicza utility wg wzoru (5) z artykułu
        # sprawdzenie czy strategia jest poprawna
        if int(np.sum(strategy_vector)) != self.SUBTASKS_COUNT[task_idx]:
            return 0.0

        times = []
        expenses = []

        for r in range(self.num_resources):
            aij = int(strategy_vector[r])
            if aij <= 0:
                continue

            base_time = float(self.EXEC_TIMES[task_idx][r])

            # czas rośnie z obciążeniem (multiplexing)
            current_load = int(load_vector[r])
            if current_load < 1: 
                current_load = 1

            actual_time = base_time * current_load 
            times.append(actual_time)

            # koszt niezależny od kolejki
            expense_per_subtask = base_time * float(self.PRICES[r])
            expenses.append(expense_per_subtask * aij)

        if not times:
            return 0.0

        # najdłuższy czas (równoległe wykonanie)
        t_turnaround = max(times)
        total_expense = sum(expenses)

        cost_value = (self.WT * t_turnaround) + (self.WE * total_expense)
        
        if cost_value <= 0: 
            return 0.0
        return 1.0 / cost_value

    def get_load_vector(self, allocation_matrix):
        # ile zadań na każdym zasobie
        return np.sum(allocation_matrix, axis=0)
    
    def get_total_system_utility(self, allocation_matrix):
        # suma utility wszystkich zadań (do GELR)
        load_vector = self.get_load_vector(allocation_matrix)
        total_u = 0.0
        for i in range(self.num_tasks):
            total_u += self.calculate_utility(i, allocation_matrix[i], load_vector)
        return total_u

    def step1_independent_optimization(self):
        # każde zadanie wybiera zasoby bez uwzględniania innych
        print(f"\n{'='*60}")
        print("KROK 1: Optymalizacja niezależna")
        print(f"{'='*60}")
        
        allocation_matrix = np.zeros((self.num_tasks, self.num_resources), dtype=int)
        dummy_load = np.ones(self.num_resources) 

        for i in range(self.num_tasks):
            # greedy - bierzemy k(i) najtańszych zasobów
            resource_costs = []
            for r in range(self.num_resources):
                t = self.EXEC_TIMES[i][r]
                p = self.PRICES[r]
                cost = (self.WT * t) + (self.WE * (t * p))
                resource_costs.append((cost, r))
            
            resource_costs.sort(key=lambda x: x[0])
            k = self.SUBTASKS_COUNT[i]
            chosen_resources = [r for (_, r) in resource_costs[:k]]
            
            for r in chosen_resources:
                allocation_matrix[i][r] = 1
            
            u_init = self.calculate_utility(i, allocation_matrix[i], dummy_load)
            print(f"S{i+1}: {allocation_matrix[i]} (utility: {u_init:.4f})")
            
        return allocation_matrix

    def step2_evolutionary_optimization(self, initial_matrix):
        # iteracyjne rozwiązywanie konfliktów
        print(f"\n{'='*60}")
        print("KROK 2: Optymalizacja ewolucyjna")
        print(f"{'='*60}")

        current_alloc = copy.deepcopy(initial_matrix)
        flag = True 
        iteration = 0
        MAX_ITERATIONS = 20

        while flag and iteration < MAX_ITERATIONS:
            flag = False
            iteration += 1
            print(f"\n--- Iteracja {iteration} ---")
            
            load_vector = self.get_load_vector(current_alloc)
            
            # szukamy zasobów z wieloma zadaniami
            candidates_res = [r for r, l in enumerate(load_vector) if l > 1]
            if not candidates_res:
                print("Brak konfliktów. Koniec.")
                break

            # sortowanie wg czasu (najpierw te najbardziej obciążone)
            candidates_with_time = []
            for r in candidates_res:
                max_t = 0
                for task_idx in range(self.num_tasks):
                    if current_alloc[task_idx][r] == 1:
                        max_t = max(max_t, self.EXEC_TIMES[task_idx][r])
                candidates_with_time.append((max_t, r))
            
            candidates_with_time.sort(key=lambda x: x[0], reverse=True)
            multiplexed_resources = [r for (_, r) in candidates_with_time]
            print(f"Przeciążone zasoby: {multiplexed_resources}")

            for j in multiplexed_resources:
                users_of_j = [i for i in range(self.num_tasks) if current_alloc[i][j] > 0]
                candidates_to_move = []

                # sprawdzamy SPELR dla każdego zadania używającego tego zasobu
                for task_idx in users_of_j:
                    u_current = self.calculate_utility(task_idx, current_alloc[task_idx], load_vector)
                    
                    best_spelr = 0.0 # Szukamy wartości ujemnych (zysk)
                    best_target = -1

                    for p in range(self.num_resources):
                        if p == j: continue
                        if current_alloc[task_idx][p] == 1: continue
                        
                        # testujemy ruch
                        temp_alloc = current_alloc.copy()
                        temp_alloc[task_idx][j] = 0
                        temp_alloc[task_idx][p] = 1
                        
                        temp_load = self.get_load_vector(temp_alloc)
                        u_new = self.calculate_utility(task_idx, temp_alloc[task_idx], temp_load)
                        
                        spelr = u_current - u_new
                        
                        if spelr < best_spelr:
                            best_spelr = spelr
                            best_target = p
                    
                    if best_target != -1:
                        candidates_to_move.append((task_idx, best_target, best_spelr))

                if not candidates_to_move:
                    continue
                
                # liczymy GELR - wybieramy ruch najbardziej opłacalny globalnie
                total_utility_before = self.get_total_system_utility(current_alloc)
                
                best_candidate_tuple = None
                min_gelr = float('inf')

                for (t_idx, tgt, sp) in candidates_to_move:
                    temp_alloc = current_alloc.copy()
                    temp_alloc[t_idx][j] = 0
                    temp_alloc[t_idx][tgt] = 1
                    
                    total_utility_after = self.get_total_system_utility(temp_alloc)
                    gelr = total_utility_before - total_utility_after
                    
                    if gelr < min_gelr:
                        min_gelr = gelr
                        best_candidate_tuple = (t_idx, tgt, sp, gelr)
                
                if best_candidate_tuple:
                    final_task, final_target, final_spelr, final_gelr = best_candidate_tuple
                    
                    print(f"  Realokacja: S{final_task+1} R{j+1}->R{final_target+1}")
                    print(f"  SPELR={final_spelr:.5f}, GELR={final_gelr:.5f}")
                    
                    current_alloc[final_task][j] = 0
                    current_alloc[final_task][final_target] = 1
                    
                    flag = True
                    break
            
            if not flag:
                print("Równowaga osiągnięta.")
        
        if iteration >= MAX_ITERATIONS:
            print("Uwaga: przekroczono limit iteracji")

        return current_alloc

if __name__ == "__main__":
    prices = [1.0, 1.2, 1.5, 1.8, 2.0]
    exec_times = [
        [6.0, 5.0, 4.0, 3.5, 3.0], 
        [5.0, 4.2, 3.6, 3.0, 2.8], 
        [4.0, 3.5, 3.2, 2.8, 2.4]  
    ]
    subtasks = [2, 3, 4]

    project = WeiCloudProject(prices, exec_times, subtasks)
    initial_alloc = project.step1_independent_optimization()
    
    print("\nAlokacja po kroku 1:")
    print(initial_alloc)
    
    final_alloc = project.step2_evolutionary_optimization(initial_alloc)
    
    print(f"\n{'='*60}")
    print("WYNIK KOŃCOWY")
    print(f"{'='*60}")
    print(final_alloc)