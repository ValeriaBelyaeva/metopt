"""Excel для ЛР2: ручное прохождение метода ломаных (каждая итерация — строка с формулами)."""
import sys
from pathlib import Path

import openpyxl
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

LAB = Path(__file__).resolve().parent.parent / "lr2"
sys.path.insert(0, str(LAB))
from python_solution import parse_function, piyavskii  # noqa: E402

A, B, L, EPS = -3, 3, 1 + 3.14159, 0.01
res = piyavskii(parse_function("x + sin(3.14159*x)"), A, B, L, EPS)
hist = res["history"]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Метод ломаных"
thin = Side(style="thin", color="999999")
BRD = Border(left=thin, right=thin, top=thin, bottom=thin)
HEAD = PatternFill("solid", fgColor="DCE6F1")
PAR = PatternFill("solid", fgColor="FFF2CC")
STOP = PatternFill("solid", fgColor="E2EFDA")
bold = Font(bold=True)

ws["A1"] = "ЛР2. Метод ломаных — ручное прохождение: W(x) = x + sin(3.14159·x) на [-3; 3]"
ws["A1"].font = Font(bold=True, size=13)
params = [("a", A), ("b", B), ("L", "=1+3.14159"), ("eps", EPS),
          ("W(a)", "=B3+SIN(3.14159*B3)"), ("W(b)", "=B4+SIN(3.14159*B4)")]
for i, (k, v) in enumerate(params):
    ws.cell(row=3 + i, column=1, value=k).font = bold
    c = ws.cell(row=3 + i, column=2, value=v)
    c.fill = PAR
    c.border = BRD
notes = [
    "L = max|W'(x)| = max|1 + π·cos(πx)| = 1 + π.  Стартовые итерации: u0 = a, u1 = b.",
    "Пересечение галочек соседних верхних вершин uл < uп:  u = (W(uл) − W(uп))/(2L) + (uл + uп)/2,  p(u) = (W(uл) + W(uп))/2 − L(uп − uл)/2.",
    "На каждой итерации берём самую низкую нижнюю вершину ломаной (её верхние вершины вписаны в строку) — это u_n,",
    "вычисляем W(u_n) — новая верхняя вершина; её галочка g_n заменяет нижнюю вершину двумя новыми (слева и справа).",
    "Остановка (как в лекции): W(u_n) − p_{n−1}(u_n) < eps; ответ u* = u_n, W* = W(u_n).",
]
for i, t in enumerate(notes):
    ws.cell(row=3 + i, column=4, value=t).font = Font(italic=True, color="555555")

HR = 10
head = ["n", "верхние вершины (№)", "uл", "W(uл)", "uп", "W(uп)", "u_n — пересечение", "p_{n−1}(u_n)",
        "W(u_n)", "W(u_n) − p", "№ точки u", "статус"]
for j, t in enumerate(head, 1):
    c = ws.cell(row=HR, column=j, value=t)
    c.font = bold
    c.fill = HEAD
    c.border = BRD
    c.alignment = Alignment(horizontal="center", wrap_text=True)


def ref(i):
    """Ячейки (u, W(u)) верхней вершины с номером i: 0 = a, 1 = b, i >= 2 — точка итерации i - 1."""
    if i == 0:
        return "$B$3", "$B$7"
    if i == 1:
        return "$B$4", "$B$8"
    r = HR + (i - 1)
    return f"$G${r}", f"$I${r}"


for h in hist:
    k = h["k"]
    r = HR + k
    xl, fl = ref(h["il"])
    xr, fr = ref(h["ir"])
    row = [k, f"{h['il']} и {h['ir']}", f"={xl}", f"={fl}", f"={xr}", f"={fr}",
           f"=(D{r}-F{r})/(2*$B$5)+(C{r}+E{r})/2",
           f"=(D{r}+F{r})/2-$B$5*(E{r}-C{r})/2",
           f"=G{r}+SIN(3.14159*G{r})",
           f"=I{r}-H{r}",
           k + 1,
           f'=IF(J{r}<$B$6,"СТОП: W(u)-p(u) < eps","продолжаем")']
    for j, v in enumerate(row, 1):
        c = ws.cell(row=r, column=j, value=v)
        c.border = BRD
        if 3 <= j <= 10:
            c.number_format = "0.00000"
        if h["stop"]:
            c.fill = STOP

last = HR + len(hist)
ans = last + 2
ws.cell(row=ans, column=1, value="Ответ").font = Font(bold=True, size=12)
answer = [("u* ≈", f"=G{last}"), ("W(u*) ≈", f"=I{last}"), ("итераций (после стартовых)", f"=COUNT(A{HR + 1}:A{last})"),
          ("W(u*) − p(u*)", f"=J{last}")]
for i, (k, v) in enumerate(answer, 1):
    ws.cell(row=ans + i, column=1, value=k).font = bold
    c = ws.cell(row=ans + i, column=2, value=v)
    c.fill = STOP
    if i != 3:
        c.number_format = "0.00000"

widths = [6, 12, 10, 10, 10, 10, 13, 12, 11, 11, 8, 24]
for j, w in enumerate(widths, 1):
    ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w
ws.freeze_panes = ws.cell(row=HR + 1, column=1)

# ------------------------------------------------ лист с графиком
g = wb.create_sheet("График")
g["A1"], g["B1"] = "x", "f(x)"
N = 240
for i in range(N + 1):
    g.cell(row=2 + i, column=1, value=f"={A}+{(B - A) / N}*{i}")
    g.cell(row=2 + i, column=2, value=f"=A{2 + i}+SIN(3.14159*A{2 + i})")
ch = ScatterChart()
ch.title = "W(x) и верхние вершины ломаной"
ch.x_axis.title = "x"
ch.y_axis.title = "f(x)"
ch.height, ch.width = 10, 20
s1 = Series(Reference(g, min_col=2, min_row=2, max_row=N + 2),
            Reference(g, min_col=1, min_row=2, max_row=N + 2), title="W(x)")
s1.marker.symbol = "none"
s1.smooth = True
s2 = Series(Reference(ws, min_col=9, min_row=HR + 1, max_row=last),
            Reference(ws, min_col=7, min_row=HR + 1, max_row=last), title="верхние вершины u_n")
s2.marker.symbol = "circle"
s2.marker.size = 5
s2.graphicalProperties.line.noFill = True
ch.series += [s1, s2]
g.add_chart(ch, "D2")

wb.save(LAB / "excel_solution.xlsx")
print("saved", len(hist), "rows; iterations =", res["iterations"])
