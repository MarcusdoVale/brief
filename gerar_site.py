#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_site.py — gera o index.html do site (layout bonito e responsivo).

Reusa as mesmas fontes gratuitas do focus_brief.py (Focus/BCB, cotacoes stooq,
agenda IBGE, Copom/FOMC) e monta UM index.html estilizado (celular + PC).
Roda no seu PC e na nuvem (GitHub Actions).
"""
import os
import re
import datetime as dt

import focus_brief as fb

OUT = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{
  --bg:#0e0e0f; --panel:#1b1b1d; --panel2:#232326; --line:#313134;
  --ink:#f4f4f5; --muted:#a0a0a6; --gold:#f2c200; --gold-soft:#3a3208;
  --up:#28c76f; --down:#ff5b5b;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
 line-height:1.55;-webkit-text-size-adjust:100%;
 background-image:radial-gradient(1200px 400px at 50% -140px,rgba(242,194,0,.10),transparent)}
.wrap{max-width:940px;margin:0 auto;padding:18px}
header.top{background:#000;border:1px solid #2a2a2c;border-radius:20px;
 padding:26px 26px;margin-bottom:16px;position:relative;overflow:hidden;
 box-shadow:0 10px 30px rgba(0,0,0,.45)}
header.top:before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;
 background:var(--gold)}
header.top h1{margin:0;font-family:"Poppins","Inter",sans-serif;
 font-size:26px;font-weight:700;letter-spacing:-.01em;color:#fff}
header.top h1 b{color:var(--gold);font-weight:700}
header.top .sub{margin-top:8px;font-size:13px;color:#c9c9cf}
.badge{display:inline-flex;align-items:center;gap:7px;background:rgba(242,194,0,.12);
 border:1px solid rgba(242,194,0,.4);color:var(--gold);padding:5px 12px;
 border-radius:999px;font-size:12px;font-weight:600;margin-top:14px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--up);
 box-shadow:0 0 0 3px rgba(40,199,111,.25)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;
 padding:18px 20px;margin:14px 0;box-shadow:0 4px 16px rgba(0,0,0,.25)}
.card h2{margin:0 0 12px;font-family:"Poppins","Inter",sans-serif;font-size:16px;
 color:#fff;font-weight:600;display:flex;align-items:center;gap:9px}
.card h2:before{content:"";width:9px;height:9px;border-radius:2px;
 background:var(--gold);display:inline-block}
.card.parecer{border:1px solid #3a3308;
 background:linear-gradient(180deg,rgba(242,194,0,.06),rgba(242,194,0,0)) , var(--panel)}
.veredito{background:rgba(40,199,111,.12);border:1px solid rgba(40,199,111,.45);
 border-radius:12px;padding:13px 15px;font-size:15px;margin:2px 0 12px;color:#eafff2}
.veredito.sell{background:rgba(255,91,91,.12);border-color:rgba(255,91,91,.45);color:#ffecec}
h3.sub{font-size:12px;color:var(--gold);text-transform:uppercase;
 letter-spacing:.05em;margin:18px 0 6px;font-weight:700}
p{margin:8px 0}
.note{color:var(--muted);font-size:12.5px}
.table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0;
 border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:440px}
th,td{padding:10px 13px;text-align:left;border-bottom:1px solid var(--line)}
th{background:var(--panel2);color:var(--gold);font-weight:600;white-space:nowrap;
 text-transform:uppercase;font-size:11.5px;letter-spacing:.03em}
tbody tr:last-child td{border-bottom:none}
tbody tr:nth-child(even){background:#161618}
.up{color:var(--up);font-weight:700}
.down{color:var(--down);font-weight:700}
footer{color:var(--muted);font-size:12px;text-align:center;margin:20px 6px 12px}
@media(max-width:600px){
 .wrap{padding:11px}
 header.top{padding:20px 18px}
 header.top h1{font-size:21px}
 .card{padding:14px 15px}
 table{font-size:13px}
}
"""


def _inline(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def _color_cell(text):
    if "▲" in text:   # ▲
        return '<span class="up">%s</span>' % text
    if "▼" in text:   # ▼
        return '<span class="down">%s</span>' % text
    return text


def _flush_table(buf):
    rows = []
    for ln in buf:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells)
    if not rows:
        return ""
    out = ['<div class="table-wrap"><table>']
    out.append("<thead><tr>" + "".join("<th>%s</th>" % _inline(c) for c in rows[0]) + "</tr></thead>")
    if len(rows) > 1:
        out.append("<tbody>")
        for r in rows[1:]:
            out.append("<tr>" + "".join("<td>%s</td>" % _color_cell(_inline(c)) for c in r) + "</tr>")
        out.append("</tbody>")
    out.append("</table></div>")
    return "".join(out)


def render_html(md):
    lines = md.split("\n")

    title = "Panorama de Mercado"
    subtitle = ""
    body_start = 0
    for idx, ln in enumerate(lines):
        if ln.startswith("# "):
            title = ln[2:].strip().replace("Brief de Mercado", "Panorama de Mercado")
            j = idx + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith("_"):
                subtitle = lines[j].strip().strip("_")
                body_start = j + 1
            else:
                body_start = idx + 1
            break
    rest = lines[body_start:]

    html = []
    updated = ""
    m = re.search(r"Atualizado às\s*([0-9:]+)", subtitle)
    if m:
        updated = m.group(1)
    # separa "Panorama de Mercado" da data
    partes = title.split("—", 1)
    nome = partes[0].strip()
    data = partes[1].strip() if len(partes) > 1 else ""
    nome_html = nome.replace("Mercado", "<b>Mercado</b>")
    sub = data
    if updated:
        sub = (sub + " · " if sub else "") + "atualizado às %s" % updated
    html.append('<header class="top">')
    html.append("<h1>%s</h1>" % nome_html)
    html.append('<div class="sub">%s · fontes oficiais gratuitas (BCB, IBGE, stooq)</div>'
                % (sub or "leitura de mercado"))
    html.append('<span class="badge"><span class="dot"></span> ao vivo · atualiza sozinho a cada 30 min</span>')
    html.append("</header>")

    section_open = False
    tbl = []
    footer_lines = []
    in_footer = False

    def close_section():
        nonlocal section_open
        if section_open:
            html.append("</div>")
            section_open = False

    idx = 0
    n = len(rest)
    while idx < n:
        ln = rest[idx].rstrip()
        s = ln.strip()

        if s == "---":
            if tbl:
                html.append(_flush_table(tbl)); tbl = []
            in_footer = True
            idx += 1
            continue

        if in_footer:
            if s:
                footer_lines.append(re.sub(r"_", "", s))
            idx += 1
            continue

        if s.startswith("## "):
            if tbl:
                html.append(_flush_table(tbl)); tbl = []
            close_section()
            t2 = s[3:].strip()
            cls = "card parecer" if "Parecer" in t2 else "card"
            html.append('<div class="%s">' % cls)
            html.append("<h2>%s</h2>" % _inline(t2))
            section_open = True
            idx += 1
            continue

        if s.startswith("|"):
            tbl.append(ln)
            idx += 1
            continue
        elif tbl:
            html.append(_flush_table(tbl)); tbl = []

        if not s:
            idx += 1
            continue

        if not section_open:
            html.append('<div class="card">'); section_open = True

        if s.startswith("_") and s.endswith("_") and len(s) > 1:
            html.append('<p class="note">%s</p>' % _inline(s.strip("_")))
        elif re.match(r"^\*\*VEREDITO", s):
            sell = "vendedor" in s.lower()
            html.append('<div class="veredito%s">%s</div>'
                        % (" sell" if sell else "", _inline(s)))
        elif re.match(r"^\*\*.+\*\*$", s):
            html.append('<h3 class="sub">%s</h3>' % re.sub(r"\*\*", "", s))
        else:
            html.append("<p>%s</p>" % _inline(s))
        idx += 1

    if tbl:
        html.append(_flush_table(tbl))
    close_section()

    foot = " · ".join([f for f in footer_lines if f.strip()]) or "Não é recomendação de investimento."

    page = []
    page.append("<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>")
    page.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    page.append("<title>%s</title>" % title)
    page.append("<meta http-equiv='refresh' content='%d'>" % fb.REFRESH_SEG)
    page.append("<link rel='preconnect' href='https://fonts.googleapis.com'>")
    page.append("<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>")
    page.append("<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700"
                "&family=Poppins:wght@600;700&display=swap' rel='stylesheet'>")
    page.append("<style>%s</style>" % CSS)
    page.append("</head><body><div class='wrap'>")
    page.append("\n".join(html))
    page.append('<footer>%s</footer>' % foot)
    page.append("</div></body></html>")
    return "\n".join(page)


def main():
    try:
        focus = fb.pegar_focus()
    except Exception:
        focus = {}
    try:
        cotacoes = fb.pegar_cotacoes()
    except Exception:
        cotacoes = []
    try:
        agenda = fb.pegar_agenda()
    except Exception:
        agenda = []
    try:
        sgs = fb.pegar_sgs()
    except Exception:
        sgs = []

    variacao, prev_fmt = {}, None
    try:
        con = fb.hist_conectar()
        variacao, prev_fmt = fb.variacao_desde_ultima(focus, con)
        fb.salvar_historico(focus, con)
        con.close()
    except Exception:
        pass

    parecer = fb.ler_parecer()
    md = fb.montar_brief(focus, agenda, variacao, prev_fmt, sgs, cotacoes, parecer)
    html = render_html(md)

    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html gerado em", OUT)


if __name__ == "__main__":
    main()
