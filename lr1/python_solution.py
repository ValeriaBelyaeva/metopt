"""
ЛР1. Решение задачи линейного программирования симплекс-методом.
Беляева Валерия Андреевна, K3339, поток 1.3, вариант 6.

Метод — как на практике: сокращённая симплекс-таблица
(строки — базисные переменные, столбцы — свободные переменные и b,
последняя строка — коэффициенты целевой функции и -Q в углу).
Пересчёт таблицы — по правилам а)–г) (метод Жордана–Гаусса).
Вычисления ведутся в обыкновенных дробях (fractions.Fraction),
поэтому промежуточные таблицы совпадают с ручным решением.

Готовые реализации симплекс-метода (scipy.linprog, pulp и т.п.) не используются.
"""
from fractions import Fraction
from math import floor, ceil

LE, EQ, GE = "<=", "=", ">="


# ---------------------------------------------------------------- вывод таблиц

def fmt(v):
    v = Fraction(v)
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def print_table(t, title=""):
    """Печать сокращённой симплекс-таблицы."""
    if title:
        print(title)
    w = 7
    print(" " * 6 + "".join(f"{n:>{w}}" for n in t["free"]) + f"{'b':>{w}}")
    for name, row in zip(t["basis"], t["rows"]):
        print(f"{name:>5} " + "".join(f"{fmt(v):>{w}}" for v in row))
    print(f"{t['obj_name']:>5} " + "".join(f"{fmt(v):>{w}}" for v in t["obj"]))
    print()


# ------------------------------------------------------- шаг 1: канонический вид

def to_canonical(c, constraints, sense="min", free_vars=()):
    """Приведение ЗЛП к каноническому виду.

    c           — коэффициенты целевой функции;
    constraints — список (коэффициенты, знак, правая часть), знак: '<=', '=', '>=';
    sense       — 'min' или 'max' (max f сводится к min (-f));
    free_vars   — индексы переменных без ограничения на знак (x = x' - x'').

    Возвращает словарь: матрица A, вектор b >= 0, вектор c (на минимум),
    имена переменных и способ восстановить исходные переменные.
    """
    n = len(c)
    sign = 1 if sense == "min" else -1
    names, cost, columns, recover = [], [], [], []   # recover[k] = [(номер столбца, множитель)]

    # исходные переменные (свободные расщепляем на разность двух неотрицательных)
    for k in range(n):
        col = [Fraction(a[k]) for a, _, _ in constraints]
        if k in free_vars:
            names += [f"x{k + 1}'", f"x{k + 1}''"]
            cost += [sign * Fraction(c[k]), -sign * Fraction(c[k])]
            columns += [col, [-v for v in col]]
            recover.append([(len(names) - 2, 1), (len(names) - 1, -1)])
        else:
            names.append(f"x{k + 1}")
            cost.append(sign * Fraction(c[k]))
            columns.append(col)
            recover.append([(len(names) - 1, 1)])

    # дополнительные (балансовые) переменные: +s для '<=', -s для '>='
    m = len(constraints)
    extra = n + 1
    for i, (_, rel, _) in enumerate(constraints):
        if rel == EQ:
            continue
        col = [Fraction(0)] * m
        col[i] = Fraction(1 if rel == LE else -1)
        names.append(f"x{extra}")
        extra += 1
        cost.append(Fraction(0))
        columns.append(col)

    A = [[columns[j][i] for j in range(len(columns))] for i in range(m)]
    b = [Fraction(rhs) for _, _, rhs in constraints]

    # правые части должны быть неотрицательными
    for i in range(m):
        if b[i] < 0:
            A[i] = [-v for v in A[i]]
            b[i] = -b[i]

    return {"A": A, "b": b, "c": cost, "names": names,
            "recover": recover, "sign": sign, "n_orig": n}


def print_canonical(canon):
    A, b, names = canon["A"], canon["b"], canon["names"]

    def lin(coefs):
        parts = []
        for a, nm in zip(coefs, names):
            if a == 0:
                continue
            s = "-" if a < 0 else "+"
            mag = "" if abs(a) == 1 else fmt(abs(a))
            parts.append(f"{s} {mag}{nm}")
        text = " ".join(parts) or "0"
        return text[2:] if text.startswith("+ ") else text

    print("Канонический вид:")
    print(f"  W(x) = {lin(canon['c'])} -> min")
    for row, rhs in zip(A, b):
        print(f"  {lin(row)} = {fmt(rhs)}")
    print(f"  {', '.join(names)} >= 0\n")


# ------------------------------------------------ шаг 2: вспомогательная задача

def build_auxiliary(canon):
    """Построение вспомогательной задачи.

    В строке, где уже есть «готовая» базисная переменная (единичный столбец),
    она и становится базисной; в остальные строки вводятся искусственные
    переменные. W'(x) = сумма искусственных переменных -> min.
    """
    A, b, names = canon["A"], canon["b"], canon["names"]
    m, n = len(A), len(names)

    basis = [None] * m
    for j in range(n):
        col = [A[i][j] for i in range(m)]
        nonzero = [i for i in range(m) if col[i] != 0]
        if len(nonzero) == 1 and col[nonzero[0]] == 1 and basis[nonzero[0]] is None:
            basis[nonzero[0]] = j

    art_names = []
    next_index = n + 1
    for i in range(m):
        if basis[i] is None:
            art_names.append(f"x{next_index}")
            basis[i] = art_names[-1]
            next_index += 1
        else:
            basis[i] = names[basis[i]]

    free = [nm for nm in names if nm not in basis]
    col_of = {nm: j for j, nm in enumerate(names)}
    rows = [[A[i][col_of[nm]] for nm in free] + [b[i]] for i in range(m)]

    # W' = сумма искусственных = сумма (b_i - sum a_ij x_j) по их строкам
    obj = [Fraction(0)] * (len(free) + 1)
    for i in range(m):
        if basis[i] in art_names:
            for j in range(len(free) + 1):
                obj[j] -= rows[i][j]          # в углу таблицы стоит -Q

    return {"basis": basis, "free": free, "rows": rows, "obj": obj,
            "obj_name": "W'", "artificial": set(art_names)}


# ---------------------------------------------------- шаг 3: пересчёт таблицы

def choose_pivot(t):
    """Выбор разрешающего элемента.

    Столбец — наименьший отрицательный коэффициент целевой строки
    (если таких нет — оптимум найден, возвращаем None).
    Строка — минимальное отношение b_i / a_is по a_is > 0
    (если таких нет — целевая функция не ограничена снизу).
    """
    d = t["obj"][:-1]
    s = min(range(len(d)), key=lambda j: (d[j], j)) if d else None
    if s is None or d[s] >= 0:
        return None

    ratios = [(row[-1] / row[s], i) for i, row in enumerate(t["rows"]) if row[s] > 0]
    if not ratios:
        raise ValueError("Целевая функция не ограничена снизу — решений нет")
    _, r = min(ratios)
    return r, s


def jordan_step(t, r, s):
    """Пересчёт сокращённой таблицы относительно элемента a_rs:
    а) a_rs' = 1 / a_rs;
    б) строка:  a_rj' = a_rj / a_rs;
    в) столбец: a_is' = -a_is / a_rs;
    г) остальные: a_ij' = a_ij - a_is * a_rj / a_rs.
    Базисная переменная строки r и свободная столбца s меняются местами.
    Если из базиса вышла искусственная переменная — её столбец удаляется.
    """
    rows = t["rows"] + [t["obj"]]
    p = rows[r][s]
    new = [row[:] for row in rows]
    for i in range(len(rows)):
        for j in range(len(rows[0])):
            if i == r and j == s:
                new[i][j] = 1 / p
            elif i == r:
                new[i][j] = rows[r][j] / p
            elif j == s:
                new[i][j] = -rows[i][s] / p
            else:
                new[i][j] = rows[i][j] - rows[i][s] * rows[r][j] / p

    t["basis"][r], t["free"][s] = t["free"][s], t["basis"][r]
    t["rows"], t["obj"] = new[:-1], new[-1]

    if t["free"][s] in t.get("artificial", ()):
        drop_column(t, s)


def drop_column(t, s):
    del t["free"][s]
    for row in t["rows"]:
        del row[s]
    del t["obj"][s]


def run_simplex(t, verbose=True, start=0):
    """Итерации симплекс-метода до оптимума. Возвращает номер последней таблицы."""
    k = start
    while True:
        pivot = choose_pivot(t)
        if pivot is None:
            return k
        r, s = pivot
        if verbose:
            print(f"Разрешающий элемент: строка {t['basis'][r]}, столбец {t['free'][s]}, "
                  f"a = {fmt(t['rows'][r][s])}  ({t['free'][s]} входит в базис, "
                  f"{t['basis'][r]} выходит)")
        jordan_step(t, r, s)
        k += 1
        if verbose:
            print_table(t, f"Таблица {k}:")


# ------------------------------------------------ шаг 4: переход к основной задаче

def to_main_problem(t, canon, verbose=True):
    """Переход от вспомогательной задачи к основной.

    1) Проверяем, что min W' = 0, иначе допустимых решений нет.
    2) Если искусственная переменная осталась в базисе (на нулевом уровне),
       выводим её, либо удаляем строку, если она линейно зависима.
    3) Строим строку целевой функции: Z выражается через свободные переменные.
    """
    if t["obj"][-1] != 0:
        raise ValueError("min W' > 0: область допустимых решений пуста — решений нет")

    i = 0
    while i < len(t["basis"]):
        if t["basis"][i] in t["artificial"]:
            cols = [j for j, v in enumerate(t["rows"][i][:-1]) if v != 0]
            if cols:
                jordan_step(t, i, cols[0])
            else:
                del t["basis"][i]
                del t["rows"][i]
                continue
        i += 1
    for nm in [nm for nm in t["free"] if nm in t["artificial"]]:
        drop_column(t, t["free"].index(nm))

    cost = dict(zip(canon["names"], canon["c"]))
    # Z = Q + sum d_j x_j, где x_базисная = b_i - sum a_ij x_j
    obj = []
    for j, nm in enumerate(t["free"]):
        obj.append(cost[nm] - sum(cost[bn] * row[j] for bn, row in zip(t["basis"], t["rows"])))
    Q = sum(cost[bn] * row[-1] for bn, row in zip(t["basis"], t["rows"]))
    t["obj"] = obj + [-Q]
    t["obj_name"] = "W"
    t["artificial"] = set()
    if verbose:
        print("Переход к основной задаче: W(x) = "
              + f"{fmt(Q)} " + " ".join(f"{'+' if d >= 0 else '-'} "
                                       f"{'' if abs(d) == 1 else fmt(abs(d))}{nm}"
                                       for d, nm in zip(obj, t["free"])) + " -> min")
    return t


# ------------------------------------------------------------- шаг 5: ответ

def extract_answer(t, canon):
    values = {nm: Fraction(0) for nm in canon["names"]}
    for nm, row in zip(t["basis"], t["rows"]):
        if nm in values:
            values[nm] = row[-1]
    names = canon["names"]
    x = [sum(mult * values[names[col]] for col, mult in parts) for parts in canon["recover"]]
    f = canon["sign"] * (-t["obj"][-1])        # Q = -(угловой элемент)
    return x, f


def solve(c, constraints, sense="min", free_vars=(), verbose=True):
    """Полное решение ЗЛП: канонический вид -> вспомогательная задача ->
    решение -> переход к основной -> решение -> ответ."""
    canon = to_canonical(c, constraints, sense, free_vars)
    if verbose:
        print_canonical(canon)

    t = build_auxiliary(canon)
    if verbose:
        art = ", ".join(sorted(t["artificial"])) or "не нужны"
        print(f"Вспомогательная задача: искусственные переменные — {art}; "
              f"W'(x) = сумма искусственных -> min")
        print_table(t, "Таблица 0:")
    k = run_simplex(t, verbose)

    to_main_problem(t, canon, verbose)
    if verbose:
        print_table(t, f"Таблица {k + 1} (основная задача):")
    run_simplex(t, verbose, start=k + 1)

    x, f = extract_answer(t, canon)
    if verbose:
        print("Все коэффициенты целевой строки неотрицательны — оптимум найден.")
    return x, f


# ------------------------------------------------- бонус: двойственная задача

def build_dual(c, constraints):
    """Двойственная задача к min c^T x, x >= 0.
    Ограничения '<=' предварительно умножаются на -1 (приводим к '>='),
    тогда: y_i >= 0 для '>=', y_i — любого знака для '='.
    Двойственная: max b^T y, A^T y <= c."""
    rows = []
    for a, rel, rhs in constraints:
        if rel == LE:
            rows.append(([-v for v in a], GE, -rhs))
        else:
            rows.append((list(a), rel, rhs))
    b = [rhs for _, _, rhs in rows]
    dual_constraints = [([rows[i][0][k] for i in range(len(rows))], LE, c[k])
                        for k in range(len(c))]
    free = tuple(i for i, (_, rel, _) in enumerate(rows) if rel == EQ)
    return b, dual_constraints, free


# --------------------------------------- бонус: целочисленная задача (ветви и границы)

def branch_and_bound(c, constraints, sense="min", best=None, depth=0, max_depth=40):
    """Метод ветвей и границ поверх собственного симплекс-метода.
    max_depth ограничивает ветвление, если допустимая область неограничена."""
    if depth > max_depth:
        print("  " * depth + "достигнута предельная глубина ветвления — ветвь отброшена")
        return best
    try:
        x, f = solve(c, constraints, sense, verbose=False)
    except ValueError:
        return best                                   # ветвь недопустима
    better = (lambda a, b: a < b) if sense == "min" else (lambda a, b: a > b)
    if best is not None and not better(f, best[1]):
        return best                                   # отсечение по границе
    frac = [k for k, v in enumerate(x) if v.denominator != 1]
    pad = "  " * depth
    if not frac:
        print(f"{pad}целочисленное решение x = {[fmt(v) for v in x]}, f = {fmt(f)}")
        return (x, f)
    k = frac[0]
    print(f"{pad}x{k + 1} = {fmt(x[k])} нецелое -> ветвим: "
          f"x{k + 1} <= {floor(x[k])} | x{k + 1} >= {ceil(x[k])}")
    unit = [1 if j == k else 0 for j in range(len(c))]
    best = branch_and_bound(c, constraints + [(unit, LE, floor(x[k]))], sense, best,
                            depth + 1, max_depth)
    best = branch_and_bound(c, constraints + [(unit, GE, ceil(x[k]))], sense, best,
                            depth + 1, max_depth)
    return best


# ------------------------------------------------------------ вариант 6

if __name__ == "__main__":
    # Минимизировать Z = 2x1 + x2 + x3 + 3x4
    c = [2, 1, 1, 3]
    constraints = [
        ([1, 2, 0, 1], LE, 10),   # x1 + 2x2 + x4 <= 10
        ([1, 0, 1, 1], EQ, 7),    # x1 + x3 + x4  =  7
        ([0, 1, 2, 0], GE, 5),    # x2 + 2x3      >= 5
    ]

    print("=" * 60 + "\nПрямая задача (вариант 6)\n" + "=" * 60)
    x, z = solve(c, constraints, "min")
    print(f"\nОптимальная точка: x* = ({', '.join(fmt(v) for v in x)})")
    print(f"Значение целевой функции: Z(x*) = {fmt(z)}")

    print("\n" + "=" * 60 + "\nБонус 1: двойственная задача\n" + "=" * 60)
    b_dual, dual_constraints, free = build_dual(c, constraints)
    print("max " + " + ".join(f"({v})y{i + 1}" for i, v in enumerate(b_dual)))
    for a, rel, rhs in dual_constraints:
        print("  " + " + ".join(f"({v})y{i + 1}" for i, v in enumerate(a)) + f" {rel} {rhs}")
    print(f"  свободные по знаку: {', '.join(f'y{i + 1}' for i in free)}; остальные >= 0\n")
    y, w = solve(b_dual, dual_constraints, "max", free_vars=free, verbose=False)
    print(f"y* = ({', '.join(fmt(v) for v in y)}),  max = {fmt(w)}")
    print(f"Z(x*) = {fmt(z)} = W(y*) = {fmt(w)} — теорема двойственности выполняется")

    print("\n" + "=" * 60 + "\nБонус 2: целочисленная задача (x — целые)\n" + "=" * 60)
    xi, zi = branch_and_bound(c, constraints, "min")
    print(f"x* = ({', '.join(fmt(v) for v in xi)}),  Z = {fmt(zi)}")
