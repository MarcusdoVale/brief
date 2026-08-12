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
import time
import datetime as dt

# Garante horario de Brasilia mesmo rodando na nuvem (servidor em UTC)
os.environ["TZ"] = "America/Sao_Paulo"
try:
    time.tzset()
except Exception:
    pass

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
 .jmetrics{grid-template-columns:repeat(2,1fr)}
 .jgrid{grid-template-columns:1fr}
}
/* ---- motor de juros ---- */
.jmetrics{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:4px 0 12px}
.jm{background:#151517;border:1px solid var(--line);border-radius:10px;padding:9px 10px}
.jm .l{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.jm .v{font-size:17px;font-weight:700;color:#fff;margin-top:2px}
.jgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:8px 0 4px}
.jcell{background:#151517;border:1px solid var(--line);border-radius:12px;padding:12px 13px}
.jcell .jh{font-family:"Poppins","Inter",sans-serif;font-weight:600;color:#fff;
 font-size:13.5px;margin-bottom:7px}
.jcell p{margin:7px 0 0;font-size:12.5px;color:#cfcfd4}
.jchip{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;
 font-weight:700;letter-spacing:.02em}
.jchip.buy{background:rgba(40,199,111,.14);color:#3ee08a;border:1px solid rgba(40,199,111,.4)}
.jchip.sell{background:rgba(255,91,91,.14);color:#ff7b7b;border:1px solid rgba(255,91,91,.4)}
.jchip.neu{background:rgba(242,194,0,.12);color:var(--gold);border:1px solid rgba(242,194,0,.4)}
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


# ----------------------------------------------------------------------------
# MOTOR DE JUROS — viés automático pela regra da taxa neutra (sempre ao vivo)
# ----------------------------------------------------------------------------
NEUTRA_BC = 8.0     # juro real neutro (~5%) + meta de inflação (3%)
NEUTRA_MKT = 11.0   # visão de mercado, ajustada pelo risco fiscal (faixa 10,5-11,5)


def _num(v):
    try:
        return float(str(v).replace("%", "").replace(",", ".").strip())
    except Exception:
        return None


def _sgs_val(sgs, nome):
    for it in (sgs or []):
        if it.get("nome") == nome:
            return _num(it.get("valor"))
    return None


def _selic_focus_por_ano(focus):
    out = {}
    for chave, r in (focus or {}).items():
        try:
            ind, ref = chave
        except Exception:
            continue
        if ind != "Selic" or not ref:
            continue
        m = re.search(r"(\d{4})", str(ref))
        v = _num(r.get("Mediana"))
        if m and v is not None:
            out[int(m.group(1))] = v
    return out


def _dolar_vivo(cotacoes, sgs):
    for it in (cotacoes or []):
        if "lar" in (it.get("nome", "").lower()):   # "Dólar (USD/BRL)"
            try:
                return float(it.get("valor")), it.get("var", "")
            except Exception:
                pass
    v = _sgs_val(sgs, "Dólar venda (R$)")
    return (v, "") if v is not None else (None, "")


def _chip(txt, tipo):
    return '<span class="jchip %s">%s</span>' % (tipo, txt)


def bloco_juros(focus, sgs, cotacoes):
    """Calcula o viés por ativo pela regra da taxa neutra sobre dados ao vivo."""
    selic = _sgs_val(sgs, "Selic meta (% a.a.)")
    ipca12 = _sgs_val(sgs, "IPCA acum. 12m (%)")
    dol, _dvar = _dolar_vivo(cotacoes, sgs)
    selic_ano = _selic_focus_por_ano(focus)

    # direção do ciclo pela trajetória projetada (Focus) — anos ordenados
    ciclo, ciclo_ico = "estável", "▬"
    if len(selic_ano) >= 2:
        anos = sorted(selic_ano)
        prim, ult = selic_ano[anos[0]], selic_ano[anos[-1]]
        if ult < prim - 0.25:
            ciclo, ciclo_ico = "cortando", "▼"
        elif ult > prim + 0.25:
            ciclo, ciclo_ico = "subindo", "▲"

    if selic is None:
        return ('<div class="card"><h2>Motor de juros — viés automático</h2>'
                '<p class="note">Aguardando os dados do Banco Central para calcular o '
                'viés. Recarregue em instantes.</p></div>')

    juro_real = (selic - ipca12) if ipca12 is not None else None
    regime = ("restritivo" if selic > NEUTRA_MKT
              else "neutro" if selic >= NEUTRA_BC else "expansionista")
    gap = selic - NEUTRA_MKT

    # ---- Dólar ----
    if selic > NEUTRA_MKT:
        if ciclo == "cortando" and gap <= 1.5:
            d_chip, d_tipo = "NEUTRO", "neu"
            d_txt = ("juro alto ainda segura o dólar, mas já perto da neutra e caindo "
                     "— o suporte do real diminui; viés migrando de vendido para neutro.")
        else:
            d_chip, d_tipo = "VENDIDO", "sell"
            d_txt = "Selic acima da neutra atrai capital e segura o dólar — vender nos repiques."
            if ciclo == "cortando":
                d_txt += " Perdendo força com o ciclo de corte."
    elif selic < NEUTRA_BC:
        d_chip, d_tipo = "COMPRADO", "buy"
        d_txt = "juro abaixo da neutra: capital sai e compra dólar — comprar nas quedas."
    else:
        d_chip, d_tipo = "NEUTRO", "neu"
        d_txt = "Selic dentro da faixa neutra: sem prêmio claro — operar o range."

    # ---- Índice ----
    if ciclo == "cortando":
        i_chip, i_tipo = "COMPRADO", "buy"
        i_txt = "juro caindo tende a favorecer a bolsa; pese o risco global."
    elif ciclo == "subindo":
        i_chip, i_tipo = "VENDIDO", "sell"
        i_txt = "juro subindo pesa sobre múltiplos e desconto de fluxo."
    else:
        i_chip, i_tipo = "NEUTRO", "neu"
        i_txt = "sem tendência clara de juros: operar por níveis."

    # ---- DI (juros) ----
    if ciclo == "cortando":
        di_chip, di_tipo = "TAXA ↓", "buy"
        di_txt = "ciclo de corte puxa a curva para baixo. Choque fiscal/risco inverte (taxa ↑)."
    elif ciclo == "subindo":
        di_chip, di_tipo = "TAXA ↑", "sell"
        di_txt = "ciclo/risco empurra a curva para cima — a favor da alta da taxa."
    else:
        di_chip, di_tipo = "LATERAL", "neu"
        di_txt = "curva sem direção: segue o próximo Copom e choques de risco."

    def f2(v):
        return ("%.2f" % v).replace(".", ",") if v is not None else "–"

    metrics = (
        '<div class="jmetrics">'
        '<div class="jm"><div class="l">Selic</div><div class="v">%s%%</div></div>'
        '<div class="jm"><div class="l">Juro real</div><div class="v">%s</div></div>'
        '<div class="jm"><div class="l">Neutra ref.</div><div class="v">~8–11%%</div></div>'
        '<div class="jm"><div class="l">Ciclo</div><div class="v">%s %s</div></div>'
        '<div class="jm"><div class="l">USD/BRL</div><div class="v">%s</div></div>'
        '</div>'
    ) % (f2(selic),
         ("~%s%%" % f2(juro_real)) if juro_real is not None else "–",
         ciclo_ico, ciclo,
         ("R$ %s" % f2(dol)) if dol is not None else "–")

    grid = (
        '<div class="jgrid">'
        '<div class="jcell"><div class="jh">Dólar</div>%s<p>%s</p></div>'
        '<div class="jcell"><div class="jh">Índice</div>%s<p>%s</p></div>'
        '<div class="jcell"><div class="jh">DI (juros)</div>%s<p>%s</p></div>'
        '</div>'
    ) % (_chip(d_chip, d_tipo), d_txt,
         _chip(i_chip, i_tipo), i_txt,
         _chip(di_chip, di_tipo), di_txt)

    regime_txt = {
        "restritivo": ("Política <b>restritiva</b>: Selic acima da neutra — juro real alto "
                       "atrai capital e tende a segurar o câmbio."),
        "neutro": "Selic próxima da faixa neutra — política perto do equilíbrio.",
        "expansionista": ("Política <b>expansionista</b>: Selic abaixo da neutra — favorece "
                          "saída de capital e alta do dólar."),
    }[regime]

    out = ['<div class="card">',
           '<h2>Motor de juros — viés automático</h2>',
           metrics,
           '<p>%s</p>' % regime_txt,
           grid,
           '<p class="note">Calculado pela regra da taxa neutra sobre os dados ao vivo '
           '(Selic, ciclo projetado no Focus e câmbio). Leitura de cenário — não é '
           'recomendação de investimento.</p>',
           '</div>']
    return "\n".join(out)


METODO_LOGICA = """
<div class="card">
<h2>Como eu leio o mercado pelos juros</h2>
<p><b>A régua é a taxa neutra</b> = juro real neutro (~5%) + meta de inflação (3%) ≈ ~8%
nominal; ajustada pelo risco fiscal, trabalho ~11%. É o que diz se a política está apertada
ou frouxa — e define o viés antes de olhar gráfico.</p>
<div class="table-wrap"><table>
<thead><tr><th>Cenário de juros</th><th>Dólar</th><th>Por quê</th></tr></thead>
<tbody>
<tr><td>Selic <b>acima</b> da neutra (restritivo)</td><td><span class="jchip sell">vendido</span></td><td>atrai capital estrangeiro; segura o câmbio</td></tr>
<tr><td>Selic <b>abaixo</b> da neutra (expansão)</td><td><span class="jchip buy">comprado</span></td><td>capital sai e compra dólar</td></tr>
<tr><td><b>Choque de risco</b> (fiscal/externo)</td><td><span class="jchip neu">DI: taxa ↑</span></td><td>o juro futuro é a 1ª porta de estrangeiros/institucionais</td></tr>
</tbody>
</table></div>
<h3 class="sub">Direção e diferencial</h3>
<p>Além do nível, vale a <b>direção</b> (cortando/subindo) e o <b>diferencial vs Fed</b>:
enquanto a Selic fica bem acima do juro americano, o Brasil atrai recurso e segura o câmbio.
Em ciclo de corte, o juro converge para a neutra e fica "menos restritivo" — o suporte do
real diminui e o viés migra para neutro/comprado.</p>
<h3 class="sub">O DI como termômetro do dólar</h3>
<p>Não preciso operar juro: no regime de risco, <b>DI e dólar andam juntos</b> — taxa sobe,
dólar sobe; taxa cai, dólar cai. Dois cuidados: confirme o gráfico em <b>taxa (% a.a.)</b>,
não em PU (inverte); e veja o <b>porquê</b> — se o juro sobe por risco anda com o dólar, se
sobe por carry (Selic atraindo capital) pode inverter. Uso o DI como <b>confirmação</b>:
dólar subindo com DI subindo = convicção; DI parado = divergência, repique sem fôlego.</p>
<h3 class="sub">O instrumento: DI futuro</h3>
<p>É o juro futuro de 1 dia; a cotação é a taxa projetada (código DI1 + mês + ano, ex.:
DI1F29 = jan/2029; contrato de R$ 100 mil no vencimento, preço = PU). Trabalho o <b>miolo da
curva (~2–3 anos)</b>: a ponta curta é "morta" e a longa seca liquidez — o miolo precifica o
resto do ciclo e o risco fiscal, com boa liquidez. É o jeito mais direcional e barato de
traduzir a leitura de juros.</p>
<h3 class="sub">Meu fluxo</h3>
<p>1) leio o ciclo de juros (Selic vs neutra + Copom) &rarr; viés · 2) marco o range do ativo
· 3) escolho o instrumento (Dólar, Índice ou DI) · 4) espero o preço no extremo do range
alinhado ao viés · 5) executo com alarmes nas bordas.</p>
</div>
"""


def render_html(md, focus=None, sgs=None, cotacoes=None):
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
    html.append('<div class="sub">%s · Fontes: Banco Central do Brasil (Focus, SGS, Copom), '
                'IBGE, Federal Reserve e stooq</div>'
                % (sub or "leitura de mercado"))
    html.append('<span class="badge"><span class="dot"></span> atualiza a cada evento da agenda econômica</span>')
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

    # Fusão: motor de juros (viés ao vivo) + a lógica fixa do método
    html.append(bloco_juros(focus, sgs, cotacoes))
    html.append(METODO_LOGICA)

    foot = "Não é recomendação de investimento — ferramenta de apoio à decisão."

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
        mundo = fb.pegar_indices_mundo()
    except Exception:
        mundo = []
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
    md = fb.montar_brief(focus, agenda, variacao, prev_fmt, sgs, cotacoes, parecer, mundo)
    # Remove menções a "grátis/gratuita" (impressão amadora)
    md = md.replace("de fonte gratuita (stooq)", "(stooq)")
    md = md.replace("gratuita ", "").replace("gratuitas ", "").replace("grátis", "")

    # Polimento de texto: acentuação correta (PT-BR) e linguagem menos tosca
    polir = {
        "económica": "econômica",
        "projecoes": "projeções",
        "das projeções.": "das projeções.",
        "barateia o crédito": "reduz o custo do crédito",
        "barateia crédito": "reduz o custo do crédito",
        "empurrando dinheiro para as ações": "direcionando o dinheiro para as ações",
        "empurrando dinheiro para as acoes": "direcionando o dinheiro para as ações",
    }
    for a, b in polir.items():
        md = md.replace(a, b)

    html = render_html(md, focus, sgs, cotacoes)

    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html gerado em", OUT)


if __name__ == "__main__":
    main()
