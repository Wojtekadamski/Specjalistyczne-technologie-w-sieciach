# Instrukcja Odpalania Skryptu `algorytm_global_2.py`

## Spis Treści
1. [Przygotowanie Środowiska](#1-przygotowanie-środowiska)
2. [Parametry Symulacji](#2-parametry-symulacji)
3. [Przykłady Odpalania](#3-przykłady-odpalania)
4. [Scenariusze Badawcze](#4-scenariusze-badawcze)
5. [Interpretacja Wyników](#5-interpretacja-wyników)
6. [Rozwiązywanie Problemów](#6-rozwiązywanie-problemów)

---

## 1. Przygotowanie Środowiska

### Wymagania
- Docker (zainstalowany i uruchomiony)
- Bash/Shell
- Katalog `/results/` w projekcie (zostanie stworzony automatycznie)

### Zbudowanie Obrazu Docker
Wykonaj to raz, w katalogu projektu:

```bash
docker build -t cloud-sim .
```

**Wyjaśnienie:**
- `-t cloud-sim` — tagi obraz jako "cloud-sim"
- `.` — używa Dockerfile z bieżącego katalogu

### Weryfikacja Instalacji
```bash
docker run --rm cloud-sim python -c "import cvxpy; print('OK')"
```

Jeśli zobaczysz `OK`, środowisko jest gotowe.

---

## 2. Parametry Symulacji

### Tabela Parametrów

| Flaga | Domyślnie | Opis | Wpływ na Wyniki |
|-------|-----------|------|-----------------|
| `--multiplier` | 1.5 | Tłok w chmurze (Resource Scarcity). Stosunek pojemności chmury do sumy wymagań minimalnych. | **1.1**: Kryzys. Bardzo mało zasobów (10% zapasu).<br>**2.0**: Nadmiar. Chmura ma dużo wolnej mocy. |
| `--min_req` | 1.0 | Minimalne żądanie zadania. Dolna granica losowania wielkości zadania. | Wpływa na rozmiar najmniejszych zadań. |
| `--max_req` | 100.0 | Maksymalne żądanie zadania. Górna granica losowania. | **1-100**: Wysoką heterogeniczność (małe i duże zadania razem). Kluczowe dla pokazania przewagi metody Wei.<br>**10-12**: Środowisko jednorodne. Metody działają podobnie. |
| `--users` | 60 | Liczba użytkowników (Oś X). Maksymalna liczba zadań w klastrze. | Zwiększenie do 100 pokazuje skalowalność. |
| `--iter` | 15 | Liczba iteracji. Ile razy powtórzyć eksperyment dla jednego punktu na wykresie. | Większa liczba (np. 50) = gładszy wykres (mniejszy szum), ale dłuższy czas. |

### Szczegółowy Opis Parametrów

#### `--multiplier` (Tłok Zasobów)
- **Definicja:** `Cloud_Capacity / Sum_of_Min_Requirements`
- **Wpływ:** Określa, ile "poduszki" mamy w zasobach chmury
  - **1.1** = Bardzo ciasno (tylko 10% nadwyżki) — testy stabilności
  - **1.5** = Realistycznie (50% nadwyżki) — standardowa konfiguracja
  - **2.0** = Spokojnie (100% nadwyżki) — idealne warunki

#### `--min_req` i `--max_req` (Heterogeniczność)
- **Zakres (min_req - max_req):**
  - Mały (np. 10-12) → Homogeniczne (podobne zadania)
  - Dużo (np. 1-100) → Heterogeniczne (mieszane wielkości)
- **Dla metody Wei:** Duża heterogeniczność pokazuje jej siłę (sprawiedliwość dla małych zadań)

#### `--users` (Liczba Zadań)
- Liczba równoległa do liczby zadań w symulacji
- Zwiększenie do 100+ testuje skalowalność algorytmu

#### `--iter` (Powtórzenia)
- Każda punkt na osi X jest średnią z `--iter` uruchomień
- `--iter 15` (szybko, szum) vs. `--iter 50` (dokładnie, powoli)

---

## 3. Przykłady Odpalania

### Przykład 1: Szybki Test (Domyślnie)
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py
```

**Opis:**
- Uruchamia ze wszystkimi domyślnymi parametrami
- Czas: ~2-5 minut
- Wynik: Plik PNG w `results/`

### Przykład 2: Wysoka Heterogeniczność
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.5 \
  --min_req 1 \
  --max_req 100 \
  --iter 20
```

**Opis:**
- Testuje sprawiedliwość w środowisku mieszanym ("słonie i myszy")
- Duży zakres rozmiarów (1-100) pokazuje przewagę Wei
- Wynik: Wyraźna różnica między metodą Wei (sprawiedliwa) a Proportional (niesprawiedliwa)

### Przykład 3: Stress Test - Deficyt Zasobów
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.1 \
  --min_req 5 \
  --max_req 25 \
  --iter 25
```

**Opis:**
- `--multiplier 1.1` = Tylko 10% zapasu (ekstremalne warunki)
- `--min_req 5 --max_req 25` = Mniejszy zakres dla szybszych obliczeń
- Testuje, czy algorytm Wei znajduje rozwiązanie w kryzysie
- Oczekiwany wynik: Wei stabilna, nawet przy zapaści zasobów

### Przykład 4: Test Skalowalności
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.2 \
  --users 100 \
  --min_req 1 \
  --max_req 50 \
  --iter 15
```

**Opis:**
- `--users 100` = 100 zadań (duża skala)
- Testuje, czy czas obliczeń i jakość nie degradują się
- Wynik: Potwierdzenie, że metoda Wei skaluje się liniowo

### Przykład 5: Precyzyjna Analiza (Długo)
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.5 \
  --min_req 1 \
  --max_req 100 \
  --users 200 \
  --iter 50
```

**Opis:**
- `--users 200` = Maksymalna liczba badanych punktów
- `--iter 50` = 50 powtórzeń dla każdego punktu (bardzo gładki wykres)
- Czas: ~30-60 minut
- Wynik: Czysty, czytelny wykres bez szumu

---

## 4. Scenariusze Badawcze

Poniższe komendy realizują konkretne cele badawcze opisane w raporcie.

### Scenariusz A: Wysoka Heterogeniczność (Kluczowy Dowód)
**Cel:** Wykazać, że metoda Proporcjonalna jest niesprawiedliwa dla małych zadań.

```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.5 \
  --min_req 1 \
  --max_req 100 \
  --iter 20
```

**Oczekiwany wynik:**
- **Panel 1 (Jain's Index):** Niebieska linia (Wei) na ~1.0, Pomarańczowa (Proportional) poniżej 0.9
- **Wniosek:** Wei gwarantuje matematyczną równość. Proportional faworyzuje duże zadania.

---

### Scenariusz B: Deficyt Zasobów (Stress Test)
**Cel:** Wykazać, że solver Wei znajduje rozwiązanie nawet przy 10% zapasie zasobów.

```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.1 \
  --min_req 5 \
  --max_req 25 \
  --iter 25
```

**Oczekiwany wynik:**
- Metoda Wei znajduje rozwiązanie w ekstremalnych warunkach
- Bez przerwań ani błędów numerycznych
- Wniosek: Wei jest stabilna i niezawodna

---

### Scenariusz C: Skalowalność (Wydajność)
**Cel:** Wykazać, że czas obliczeń i jakość nie degradują się przy większej skali.

```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.2 \
  --users 100 \
  --iter 15
```

**Oczekiwany wynik:**
- Panel 2 (Makespan) oraz Panel 3 (Utility) pozostają stabilne
- Brak degradacji wydajności dla N=100
- Wniosek: Wei skaluje się dobrze

---

### Scenariusz D: Środowisko Jednorodne (Porównanie)
**Cel:** Pokazać, że metody działają podobnie dla zadań o zbliżonych rozmiarach.

```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.5 \
  --min_req 10 \
  --max_req 12 \
  --iter 20
```

**Oczekiwany wynik:**
- Obie metody na podobnym poziomie
- Brak znacznej różnicy w Jain's Index
- Wniosek: Heterogeniczność to kluczowy warunek dla przewagi Wei

---

## 5. Interpretacja Wyników

Skrypt generuje plik PNG z **trzema wykresami (panelami)** na jednym rysunku.

### Plik Wyjściowy
Wykresy są zapisywane w:
```
results/cloud_allocation_comparison_TIMESTAMP.png
```

### Panel 1: Sprawiedliwość (Jain's Index)
**Oś Y:** 0.0 (Całkowicie niesprawiedliwe) — 1.0 (Idealne)  
**Oś X:** Liczba użytkowników (zadań)

**Interpretacja:**
- **Wartość 1.0** = Wszyscy otrzymują równą proporcję nadwyżki
- **Wartość 0.9** = Małe odchylenia od ideału
- **Wartość < 0.8** = Duża niesprawiedliwość

**Oczekiwany wynik:**
- 🔵 **Niebieska linia (Wei):** Powinna pozostawać na ~1.0 (idealna równość)
- 🟠 **Pomarańczowa linia (Proportional):** Zazwyczaj spada poniżej 0.9 (faworyzuje duże zadania)

**Wniosek:**
> Metoda Wei gwarantuje matematyczną równość w podziale nadwyżki poprzez wykorzystanie teorii gier (Nash Bargaining Solution).

---

### Panel 2: Czas Wykonania (Makespan)
**Oś Y:** Znormalizowany czas (im niżej, tym szybciej)  
**Oś X:** Liczba użytkowników (zadań)

**Interpretacja:**
- **Niższe wartości** = Szybsze ukończenie wszystkich zadań
- **Wyższe wartości** = Systemu zajmuje więcej czasu

**Oczekiwany wynik:**
- 🟠 **Pomarańczowa linia (Proportional):** Zazwyczaj niżej (szybciej)
- 🔵 **Niebieska linia (Wei):** Zazwyczaj wyżej (wolniej)

**Wniosek:**
> To jest **"Cena Sprawiedliwości"**. Metoda Proportional faworyzuje duże zadania (przydziela im więcej zasobów), co przyspiesza ich wykonanie i opróżnia kolejkę. Wei robi to sprawiedliwie, ale zajmuje więcej czasu, aby wyrównać wszystko.

**Przykład:**
- Proportional: 10 jednostek czasu (ale małe zadania cierpią)
- Wei: 12 jednostek czasu (ale wszyscy są traktowani sprawiedliwie)

---

### Panel 3: Globalna Użyteczność (Total Utility)
**Oś Y:** Suma logarytmów nadwyżek (im wyżej, tym lepiej)  
**Oś X:** Liczba użytkowników (zadań)

**Interpretacja:**
- **Wyższe wartości** = Większa globalna "satysfakcja" systemu
- Kryterium z teorii gier (maxsum logarytmów nadwyżek)

**Oczekiwany wynik:**
- 🔵 **Niebieska linia (Wei):** Powinna być na lub powyżej linii Proportional
- Często wypłaszcza się, podczas gdy Proportional rośnie

**Wniosek:**
> Zgodnie z Tabelą 4 w artykule Wei et al., podejście oparte na teorii gier (NBS) maksymalizuje globalną użyteczność systemu. Mimo "ceny sprawiedliwości" w czasach wykonania, system jako całość jest bardziej "zadowolony".

---

### Czytanie Wykresów — Podsumowanie

| Metrika | Wei | Proportional | Wnioski |
|---------|-----|--------------|---------|
| **Jain's Index** | ~1.0 (Ideał) | ~0.8-0.9 | Wei jest sprawiedliwa |
| **Makespan** | Wyżej (wolniej) | Niżej (szybciej) | Cena sprawiedliwości |
| **Total Utility** | Wyżej lub równo | Niżej | Wei maksymalizuje globalną użyteczność |

---

## 6. Rozwiązywanie Problemów

### Problem 1: Docker — Błąd Konstruowania Obrazu

**Błąd:**
```
ERROR: failed to solve with frontend dockerfile.v0
```

**Przyczyna:** Brak Docker Engine lub błąd w składni Dockerfile.

**Rozwiązanie:**
```bash
# Sprawdź, czy Docker jest uruchomiony
docker --version

# Jeśli nie działa, uruchom Docker:
sudo systemctl start docker  # Linux
# lub otwórz Docker Desktop (Windows/Mac)

# Spróbuj ponownie zbudować:
docker build -t cloud-sim .
```

---

### Problem 2: Błąd — `repository does not exist`

**Błąd:**
```
docker: Error response from daemon: repository does not exist
```

**Przyczyna:** Spacje w ścieżce do katalogu projektu na Linuxie, lub obraz nie został zbudowany.

**Rozwiązanie:**
```bash
# 1. Upewnij się, że ścieżka wolumenu jest w cudzysłowie (z dolarem):
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py

# 2. Lub zbuduj obraz ponownie:
docker build -t cloud-sim .

# 3. Sprawdzenie dostępnych obrazów:
docker images | grep cloud-sim
```

---

### Problem 3: Wykresy są Poszarpane / Dziwne Skoki

**Błąd:** Linie na wykresach wyglądają chaotycznie, bez gładkości.

**Przyczyna:** Zbyt mała próba statystyczna (mało iteracji = dużo szumu).

**Rozwiązanie:**
```bash
# Zwiększ parametr --iter (np. na 50)
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.5 \
  --min_req 1 \
  --max_req 100 \
  --iter 50
```

**Trade-off:** 
- `--iter 15` → Szybko (~5 min), ale szumowo
- `--iter 50` → Precyzyjnie (~20 min), ale dokładnie

---

### Problem 4: Brak Pliku Wyników w `results/`

**Błąd:** Katalog `results/` jest pusty lub nie istnieje.

**Przyczyna:** Brak uprawnień do zapisu, lub kontener uległ awarii.

**Rozwiązanie:**
```bash
# 1. Sprawdź uprawnienia:
ls -la results/

# 2. Jeśli brak katalogu, stwórz:
mkdir -p results

# 3. Uruchom ponownie z verbose output:
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py 2>&1 | tail -20
```

---

### Problem 5: Out of Memory / Kontener Zamrzni

**Błąd:** Kontener zatrzymuje się bez komunikatu błędu.

**Przyczyna:** Zbyt dużo iteracji (`--iter 500`) lub zbyt dużo użytkowników (`--users 500`).

**Rozwiązanie:**
```bash
# Zmniejsz zasoby:
docker run --rm --memory=2g -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.5 \
  --users 50 \
  --iter 20

# Lub zwiększ zasoby kontenera w Docker Desktop:
# Settings > Resources > Memory: 4GB
```

---

### Problem 6: CVXPY Nie Rozwiązuje Problemu

**Błąd w logu:**
```
Warning: Could not solve optimal problem with CVXPY. Trying scipy...
```

**Przyczyna:** Problem optymalizacyjny jest zbyt trudny dla CVXPY (np. zbyt duża skala).

**Rozwiązanie:** To jest normalne — skrypt automatycznie przełącza się na `scipy.optimize.minimize`. Wyniki będą poprawne, choć mogą być mniej precyzyjne dla bardzo dużych problemów.

---

### Problem 7: Obrazy Brudnego Linuxu

**Błąd:** Dziwne znaki lub brakuje grafiki.

**Przyczyna:** Brak zależności systemowych dla GUI (mało istotne, bo wykresy są zapisywane do pliku).

**Rozwiązanie:** Nie jest wymagane — wykresy są zapisywane, a nie wyświetlane na ekranie.

---

## 7. Zaawansowane Kombinacje Parametrów

### Konfiguracja 1: Analiza Wrażliwości na Multiplier
```bash
for mult in 1.1 1.3 1.5 1.7 2.0; do
  echo "Testing multiplier=$mult..."
  docker run --rm -v "${PWD}/results":/app/results cloud-sim \
    python algorytm_global_2.py \
    --multiplier $mult \
    --min_req 1 \
    --max_req 100 \
    --iter 20
  sleep 2
done
```

**Cel:** Pokazać, jak sprawiedliwość zmienia się z dostępnością zasobów.

---

### Konfiguracja 2: Analiza Wrażliwości na Heterogeniczność
```bash
for range in "1 10" "1 50" "1 100" "1 200"; do
  echo "Testing range: $range..."
  docker run --rm -v "${PWD}/results":/app/results cloud-sim \
    python algorytm_global_2.py \
    --multiplier 1.5 \
    --min_req $(echo $range | cut -d' ' -f1) \
    --max_req $(echo $range | cut -d' ' -f2) \
    --iter 20
  sleep 2
done
```

**Cel:** Pokazać, że heterogeniczność jest kluczowa dla przewagi Wei.

---

## 8. Glossarium Terminów

| Termin | Definicja |
|--------|-----------|
| **Multiplier** | Stosunek `Cloud_Capacity / Sum_of_Min_Requirements`. Mierzy "ciasnotę" zasobów. |
| **Jain's Index** | Miara sprawiedliwości (0–1). 1.0 = idealna równość. |
| **Makespan** | Czas wykonania najwolniejszego zadania. Niżej = szybciej. |
| **Total Utility** | Suma logarytmów nadwyżek. Mierzy globalną "satysfakcję" systemu. |
| **Wei NBS** | Nash Bargaining Solution z pracy Wei et al. Gwarantuje sprawiedliwość. |
| **Proportional** | Tradycyjna metoda DRF (Dominant Resource Fairness). Szybka, ale niesprawiedliwa. |
| **Nadwyżka (Surplus)** | `Przydzielone_Zasoby - Minimalne_Wymaganie`. To, co zadanie otrzymuje ponad minimum. |

---

## 9. Najczęściej Używane Komendy

### Szybki Test
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py
```

### Pełne Badanie (Rekomendowane)
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.5 \
  --min_req 1 \
  --max_req 100 \
  --iter 30
```

### Stress Test
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --multiplier 1.1 \
  --min_req 5 \
  --max_req 25
```

### Test Skalowalności
```bash
docker run --rm -v "${PWD}/results":/app/results cloud-sim \
  python algorytm_global_2.py \
  --users 100 \
  --iter 20
```

---

## 10. Flaga Pomocy

Aby zobaczyć wszystkie dostępne opcje:

```bash
docker run --rm cloud-sim python algorytm_global_2.py --help
```

---

**Ostatnia aktualizacja:** 14.01.2026  
**Wersja skryptu:** algorytm_global_2.py  
**Status:** ✅ Gotowy do użytku

