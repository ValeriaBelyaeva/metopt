"""
ЛР2. Метод ломаных (метод Пиявского) — глобальный экстремум липшицевой функции на отрезке.
Беляева Валерия Андреевна, K3339, поток 1.3.

Запуск:
  python3 python_solution.py                      — ввод f(x), a, b, eps (и L) с клавиатуры
  python3 python_solution.py "x + sin(3.14159*x)" -3 3 0.01 [--L 4.1416] [--max]
  python3 python_solution.py --demo               — все демонстрации из отчёта (графики в figures/)

Экстремум ищется только методом ломаных: новые точки испытаний — аналитически вычисленные
нижние вершины ломаной (точки пересечения её звеньев), верхние вершины — точки испытаний.
Равномерная сетка используется лишь для рисования графика и (если L не задана) для оценки L.
"""
import argparse
import ast
import heapq
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG_DIR = Path(__file__).resolve().parent / "figures"

# ---------------------------------------------------------------- разбор строки f(x)

_NAMES = {name: getattr(np, name) for name in
          ["sin", "cos", "tan", "exp", "sqrt", "log", "log2", "log10",
           "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "floor", "ceil", "sign"]}
_NAMES.update({"abs": np.abs, "ln": np.log, "asin": np.arcsin, "acos": np.arccos,
               "atan": np.arctan, "pi": np.pi, "e": np.e})
_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load, ast.Constant,
          ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd)


def parse_function(text):
    """Строка 'f(x) = x + sin(3.14159*x)' -> функция f(x).
    Левую часть 'f(x) =' можно не писать, '^' понимается как степень.
    Формула проверяется по белому списку (никакого произвольного eval)."""
    expr = text.strip()
    if "=" in expr:
        expr = expr.split("=", 1)[1]
    expr = expr.strip().replace("^", "**")
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _NODES):
            raise ValueError(f"Недопустимая конструкция в формуле: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id != "x" and node.id not in _NAMES:
            raise ValueError(f"Неизвестное имя в формуле: {node.id}")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
            raise ValueError("Недопустимый вызов в формуле")
    code = compile(tree, "<f(x)>", "eval")

    def f(x):
        return eval(code, {"__builtins__": {}}, {**_NAMES, "x": x})

    f.expr = expr
    return f


def to_float(value):
    """Число или строка с числом; допускается десятичная запятая ('0,01')."""
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    return float(value)


# ---------------------------------------------------------------- константа Липшица

def estimate_lipschitz(f, a, b, n=2000, reserve=1.2):
    """Оценка L, если она не задана: max |Δf/Δx| по вспомогательной сетке с запасом 20%."""
    xs = np.linspace(a, b, n + 1)
    ys = np.asarray(f(xs), dtype=float) * np.ones_like(xs)
    slope = np.max(np.abs(np.diff(ys) / np.diff(xs)))
    return max(reserve * slope, 1e-12)


# ---------------------------------------------------------------- метод ломаных

def lower_vertex(xl, fl, xr, fr, L):
    """Нижняя вершина ломаной на [xl, xr] — пересечение прямых
    y = fl - L (x - xl)  и  y = fr + L (x - xr)."""
    xv = 0.5 * (xl + xr) + (fl - fr) / (2.0 * L)
    pv = 0.5 * (fl + fr) - 0.5 * L * (xr - xl)
    return pv, xv


def piyavskii(f, a, b, L, eps, mode="min", max_iter=1_000_000):
    """Глобальный экстремум липшицевой f на [a, b] методом ломаных.
    mode = 'min' или 'max' (максимум f = минимум -f).
    Возвращает словарь с ответом, историей итераций и данными для графика."""
    if not a < b:
        raise ValueError("Должно быть a < b")
    if L <= 0 or eps <= 0:
        raise ValueError("L и eps должны быть положительными")
    sign = 1.0 if mode == "min" else -1.0
    g = lambda x: sign * float(f(x))

    t0 = time.perf_counter()
    ga, gb = g(a), g(b)
    if abs(ga - gb) > L * (b - a):
        raise ValueError("Константа L занижена: условие Липшица нарушено на концах отрезка")
    trial_x, trial_g = [a, b], [ga, gb]            # верхние вершины (точки испытаний)
    x_best, g_best = (a, ga) if ga <= gb else (b, gb)

    # куча нижних вершин: (высота, абсцисса, индекс левой точки, индекс правой точки)
    pv, xv = lower_vertex(a, ga, b, gb, L)
    heap = [(pv, xv, 0, 1)]
    history = []
    iterations = 0
    while True:
        pv, xv, il, ir = heap[0]                   # самая низкая вершина = минимум ломаной
        gap = g_best - pv
        if gap <= eps or iterations >= max_iter:
            history.append({"k": iterations + 1, "il": il, "ir": ir, "xv": xv, "pv": pv,
                            "record": g_best, "gap": gap, "stop": True})
            break
        heapq.heappop(heap)
        iterations += 1
        gv = g(xv)                                 # новое испытание
        if gv < pv - 1e-9 * max(1.0, abs(pv)):
            raise ValueError(f"Константа L занижена: f({xv:.6g}) лежит ниже ломаной")
        history.append({"k": iterations, "il": il, "ir": ir, "xv": xv, "pv": pv, "gv": gv,
                        "record": g_best, "gap": gap, "stop": False})
        trial_x.append(xv)
        trial_g.append(gv)
        new = len(trial_x) - 1
        if gv < g_best:
            x_best, g_best = xv, gv
        # вершина заменяется двумя новыми — слева и справа от новой точки
        pl, xvl = lower_vertex(trial_x[il], trial_g[il], xv, gv, L)
        pr, xvr = lower_vertex(xv, gv, trial_x[ir], trial_g[ir], L)
        heapq.heappush(heap, (pl, xvl, il, new))
        heapq.heappush(heap, (pr, xvr, new, ir))
    elapsed = time.perf_counter() - t0

    return {
        "mode": mode, "a": a, "b": b, "L": L, "eps": eps, "sign": sign,
        "x": x_best, "f": sign * g_best,             # приближённая точка и значение экстремума
        "bound": sign * heap[0][0],                  # гарантированная граница (минимум ломаной)
        "gap": g_best - heap[0][0],                  # достигнутая точность
        "iterations": iterations,
        "evaluations": len(trial_x),
        "time": elapsed,
        "converged": g_best - heap[0][0] <= eps,
        "trial_x": np.array(trial_x),
        "trial_f": sign * np.array(trial_g),
        "vert_x": np.array([h[1] for h in heap]),    # нижние вершины итоговой ломаной
        "vert_p": sign * np.array([h[0] for h in heap]),
        "history": history,
    }


# ---------------------------------------------------------------- визуализация

def broken_line(res):
    """Итоговая ломаная: чередование точек испытаний и нижних вершин."""
    x = np.concatenate([res["trial_x"], res["vert_x"]])
    y = np.concatenate([res["trial_f"], res["vert_p"]])
    order = np.argsort(x, kind="stable")
    return x[order], y[order]


def plot_result(f, res, title="", ax=None, max_aux=60, legend=True):
    a, b, L, sign = res["a"], res["b"], res["L"], res["sign"]
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(10, 5.2))
    xx = np.linspace(a, b, 2000)                     # сетка только для рисования
    yy = np.asarray(f(xx), dtype=float) * np.ones_like(xx)
    ax.plot(xx, yy, color="#1f4e9c", lw=1.8, label="f(x)", zorder=3)
    if len(res["trial_x"]) <= max_aux:               # вспомогательные функции f(x_i) ∓ L|x - x_i|
        for i, (xi, fi) in enumerate(zip(res["trial_x"], res["trial_f"])):
            ax.plot(xx, fi - sign * L * np.abs(xx - xi), color="#9aa0a6", lw=0.6, ls="--",
                    label="вспомогательные функции" if i == 0 else None, zorder=1)
    bx, by = broken_line(res)
    ax.plot(bx, by, color="#d9480f", lw=1.3, label="итоговая ломаная", zorder=2)
    ax.plot(res["trial_x"], res["trial_f"], ".", color="#333333", ms=4,
            label=f"точки испытаний ({res['evaluations']})", zorder=4)
    kind = "минимум" if res["mode"] == "min" else "максимум"
    ax.plot([res["x"]], [res["f"]], "*", color="#2b8a3e", ms=17, mec="black", mew=0.7, zorder=5,
            label=f"{kind}: x ≈ {res['x']:.5f}, f ≈ {res['f']:.5f}")
    ax.axvline(res["x"], color="#2b8a3e", lw=0.8, ls=":", zorder=1)
    span = max(yy.max() - yy.min(), 1e-9)
    lo, hi = yy.min() - 0.12 * span, yy.max() + 0.12 * span
    if res["mode"] == "min":
        lo = min(lo, max(by.min(), yy.min() - 0.6 * span) - 0.05 * span)
    else:
        hi = max(hi, min(by.max(), yy.max() + 0.6 * span) + 0.05 * span)
    ax.set_ylim(lo, hi)
    ax.set_xlim(a, b)
    ax.set_xlabel("x")
    ax.set_ylabel("f(x)")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    if legend:
        ax.legend(loc="best", fontsize=8.5)
    if own:
        fig.tight_layout()
        return fig


def plot_steps(f, a, b, L, steps=(1, 2, 4, 8), mode="min"):
    """Как уточняется ломаная на первых итерациях."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for ax, k in zip(axes.ravel(), steps):
        res = piyavskii(f, a, b, L, eps=1e-12, mode=mode, max_iter=k)
        plot_result(f, res, title=f"итераций: {k}", ax=ax, legend=False)
    fig.suptitle("Вспомогательные функции и ломаная на первых итерациях")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- запуск

def solve(func_str, a, b, eps, L=None, mode="min", fig_name=None):
    """Разбор функции, метод ломаных, печать результатов, график."""
    f = parse_function(func_str)
    a, b, eps = to_float(a), to_float(b), to_float(eps)
    auto = L is None
    L = estimate_lipschitz(f, a, b) if auto else to_float(L)
    res = piyavskii(f, a, b, L, eps, mode=mode)

    kind = "минимум" if mode == "min" else "максимум"
    print(f"Функция:            f(x) = {f.expr}")
    print(f"Отрезок:            [{a:g}, {b:g}],  eps = {eps:g},  ищем {kind}")
    print(f"Константа Липшица:  L = {L:.6g}" + ("  (оценка по сетке с запасом 20%)" if auto else "  (задана)"))
    print(f"Аргумент:           x* ≈ {res['x']:.8f}")
    print(f"Значение функции:   f(x*) ≈ {res['f']:.8f}")
    print(f"Граница по ломаной: {res['bound']:.8f}   (разность {res['gap']:.3e} <= eps: {res['converged']})")
    print(f"Число итераций:     {res['iterations']}   (вычислений функции: {res['evaluations']})")
    print(f"Затраченное время:  {res['time'] * 1000:.3f} мс")

    fig = plot_result(f, res, title=f"Метод ломаных: f(x) = {f.expr},  eps = {eps:g},  L = {L:.4g}")
    if fig_name:
        FIG_DIR.mkdir(exist_ok=True)
        fig.savefig(FIG_DIR / fig_name, dpi=150)
        print(f"График:             figures/{fig_name}")
    plt.close(fig)
    print()
    return res


def demo():
    """Демонстрации из отчёта."""
    FIG_DIR.mkdir(exist_ok=True)
    print("=== 1. Пример из задания: f(x) = x + sin(3.14159x) на [-3, 3] ===")
    solve("f(x) = x + sin(3.14159*x)", -3, 3, "0,01", L=1 + 3.14159, fig_name="1_example.png")
    fig = plot_steps(parse_function("x + sin(3.14159*x)"), -3, 3, 1 + 3.14159)
    fig.savefig(FIG_DIR / "1_steps.png", dpi=150)
    plt.close(fig)

    print("=== 2. Функция Растригина: 10 + x^2 - 10cos(2πx) на [-3.3, 4.7] ===")
    L_rastrigin = 2 * 4.7 + 20 * np.pi
    solve("10 + x^2 - 10*cos(2*pi*x)", -3.3, 4.7, 0.01, L=L_rastrigin, fig_name="2_rastrigin.png")

    print("=== 3. Функция Экли: -20exp(-0.2|x|) - exp(cos 2πx) + 20 + e на [-4, 6] ===")
    L_ackley = 4 + 2 * np.pi * np.e
    solve("-20*exp(-0.2*abs(x)) - exp(cos(2*pi*x)) + 20 + e", -4, 6, 0.01, L=L_ackley,
          fig_name="3_ackley.png")

    print("=== 4. sin(x) + sin(10x/3) на [2.7, 7.5]: L оценивается автоматически, min и max ===")
    solve("sin(x) + sin(10*x/3)", 2.7, 7.5, 0.001, fig_name="4_min.png")
    solve("sin(x) + sin(10*x/3)", 2.7, 7.5, 0.001, mode="max", fig_name="4_max.png")

    print("=== 5. Влияние eps (Растригин) ===")
    f_r = parse_function("10 + x^2 - 10*cos(2*pi*x)")
    print(f"{'eps':>8} | {'итераций':>9} | {'время, мс':>10} | {'x*':>11} | {'f(x*)':>11} | {'сетка с той же гарантией':>24}")
    print("-" * 88)
    for eps in (1e-1, 1e-2, 1e-3, 1e-4, 1e-5):
        r = piyavskii(f_r, -3.3, 4.7, L_rastrigin, eps)
        n_grid = int(np.ceil(L_rastrigin * 8.0 / (2 * eps)))
        print(f"{eps:8g} | {r['iterations']:9d} | {r['time'] * 1000:10.3f} | {r['x']:+11.7f} | "
              f"{r['f']:11.7f} | {n_grid:24d}")


def main():
    p = argparse.ArgumentParser(description="Метод ломаных (Пиявского)")
    p.add_argument("func", nargs="?", help="функция, например \"x + sin(3.14159*x)\"")
    p.add_argument("a", nargs="?")
    p.add_argument("b", nargs="?")
    p.add_argument("eps", nargs="?")
    p.add_argument("--L", help="константа Липшица (если не задана — оценивается)")
    p.add_argument("--max", action="store_true", help="искать максимум вместо минимума")
    p.add_argument("--demo", action="store_true", help="запустить демонстрации из отчёта")
    args = p.parse_args()

    if args.demo:
        demo()
        return
    if args.func is None:                           # интерактивный ввод
        args.func = input("f(x) = ")
        args.a = input("a = ")
        args.b = input("b = ")
        args.eps = input("eps = ")
        args.L = input("L (Enter — оценить автоматически) = ") or None
    solve(args.func, args.a, args.b, args.eps, L=args.L, mode="max" if args.max else "min",
          fig_name="result.png")


if __name__ == "__main__":
    main()
