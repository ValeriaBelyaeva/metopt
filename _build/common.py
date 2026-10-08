"""Общие куски для сборки отчётов: титульный лист, стили, печать HTML -> PDF через Chrome."""
import html
import subprocess
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

AUTHOR = {
    "name": "Беляева Валерия Андреевна",
    "faculty": "ФПИиКТ",
    "group": "K3339",
    "stream": "1.3",
    "number": 6,
    "repo": "https://github.com/ValeriaBelyaeva/metopt",
}

CSS = """
@page { size: A4; margin: 18mm 17mm 18mm 22mm; }
body { font-family: 'Times New Roman', Times, serif; font-size: 12.5pt; line-height: 1.38; color: #111; }
h1 { font-size: 16pt; margin: 0 0 10px; }
h2 { font-size: 14pt; margin: 22px 0 8px; page-break-after: avoid; }
h3 { font-size: 12.5pt; margin: 16px 0 6px; page-break-after: avoid; }
p { margin: 6px 0; text-align: justify; }
.title { height: 255mm; display: flex; flex-direction: column; page-break-after: always; text-align: center; }
.title .org { font-size: 11pt; line-height: 1.3; }
.title .mid { margin-top: 60mm; }
.title .mid div { margin: 6px 0; }
.title .who { margin-top: 30mm; margin-left: auto; text-align: right; line-height: 1.8; }
.title .city { margin-top: auto; }
table.st { border-collapse: collapse; margin: 6px 0 4px; font-size: 11.5pt; page-break-inside: avoid; }
table.st td, table.st th { border: 1px solid #555; padding: 2px 9px; text-align: center; min-width: 34px; }
table.st th { background: #eef2f7; font-weight: bold; }
table.st td.pv { background: #ffe08a; font-weight: bold; }
table.st tr.obj td { border-top: 2px solid #111; }
table.st td.rowsel, table.st th.rowsel { background: #fff4cc; }
table.st td.colsel, table.st th.colsel { background: #fff4cc; }
table.grid { border-collapse: collapse; font-family: Arial, sans-serif; font-size: 9.5pt; margin: 6px 0; }
table.grid td, table.grid th { border: 1px solid #c8c8c8; padding: 2px 6px; white-space: nowrap; }
table.grid th { background: #f0f0f0; color: #555; font-weight: normal; text-align: center; }
table.grid td.n { text-align: right; }
table.grid td.var { background: #fff2cc; }
table.grid td.obj { background: #e2efda; font-weight: bold; }
table.plain { border-collapse: collapse; margin: 6px 0; font-size: 11.5pt; page-break-inside: avoid; }
table.plain td, table.plain th { border: 1px solid #777; padding: 3px 8px; vertical-align: top; }
table.plain th { background: #eef2f7; }
.tables { display: flex; flex-wrap: wrap; gap: 6px 26px; align-items: flex-start; }
.tables > div { page-break-inside: avoid; }
.cap { font-size: 11pt; font-style: italic; margin: 6px 0 0; }
.answer { border: 1.5px solid #333; padding: 6px 12px; margin: 10px 0; display: inline-block; }
pre.out { font-family: Menlo, Consolas, monospace; font-size: 8.6pt; line-height: 1.25; background: #1e1f22; color: #dcdcdc;
          padding: 8px 10px; border-radius: 4px; white-space: pre-wrap; page-break-inside: avoid; }
.code { font-size: 8.4pt; line-height: 1.25; }
.code pre { font-family: Menlo, Consolas, monospace; background: #f7f7f9; border: 1px solid #ddd; padding: 8px 10px;
            white-space: pre-wrap; margin: 6px 0; }
.note { font-size: 11pt; color: #444; border-left: 3px solid #9ab; padding: 2px 10px; margin: 8px 0; }
figure { margin: 8px 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 11pt; font-style: italic; }
ul, ol { margin: 4px 0 4px 0; padding-left: 22px; }
li { margin: 2px 0; }
ol.ru { list-style: none; counter-reset: ru; }
ol.ru li { counter-increment: ru; }
ol.ru li::before { content: counter(ru, cyrillic-lower) ") "; }
.pb { page-break-before: always; }
"""

KATEX = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body, {delimiters: [{left: '$$', right: '$$', display: true},
  {left: '$', right: '$', display: false}], throwOnError: false});"></script>
"""


def title_page(lab_no, variant_line=True):
    a = AUTHOR
    var = f"<div>Вариант: {a['number']} (mod 20) = {a['number'] % 20}</div>" if variant_line else ""
    return f"""
<div class="title">
  <div class="org">Министерство науки и высшего образования Российской Федерации<br>
  федеральное государственное автономное образовательное учреждение высшего образования<br>
  <b>«НАЦИОНАЛЬНЫЙ ИССЛЕДОВАТЕЛЬСКИЙ УНИВЕРСИТЕТ ИТМО»</b></div>
  <div class="mid">
    <div style="font-size:15pt"><b>Отчёт</b></div>
    <div>по лабораторной работе №{lab_no}</div>
    <div>по дисциплине «<b>Методы оптимизации</b>»</div>
  </div>
  <div class="who">
    <div>Автор: {a['name']}</div>
    <div>Факультет: {a['faculty']}</div>
    <div>Группа: {a['group']}</div>
    <div>Поток: {a['stream']}</div>
    {var}
  </div>
  <div class="city">Санкт-Петербург 2026</div>
</div>"""


def code_block(path):
    src = Path(path).read_text(encoding="utf-8")
    fmt = HtmlFormatter(style="friendly", noclasses=True, nowrap=False)
    return f'<div class="code">{highlight(src, PythonLexer(), fmt)}</div>'


def out_block(text):
    return f'<pre class="out">{html.escape(text)}</pre>'


def page(title, body):
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style>{KATEX}</head><body>{body}</body></html>"""


def to_pdf(html_path, pdf_path):
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", "--run-all-compositor-stages-before-draw",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                   check=True, capture_output=True)
    print("PDF:", pdf_path)
