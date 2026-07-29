#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
focus_brief.py — Coletor + interpretador de mercado (Focus/BCB + Agenda + Cotacoes)

O QUE FAZ (tudo 100% gratis, so biblioteca padrao do Python)
  1. Focus / Expectativas de Mercado — API oficial do BCB (Olinda/OData), sem chave.
  2. Cotacoes ao vivo — Ibovespa, dolar, S&P 500, Nasdaq, petroleo, ouro via stooq.com (CSV, sem chave).
  3. Realizado recente — series do BCB (SGS) + LEITURA AUTOMATICA de cada dado vs Focus.
  4. Agenda economica — calendario do IBGE + Copom + FOMC + divulgacoes do Banco Central
     (Setor Externo: Transacoes Correntes e IDP).
  5. Gera brief interpretado (Markdown + HTML) e um brief_atual.html que se auto-atualiza
     (recarrega sozinho a cada 30 min) — ideal p/ deixar uma janela aberta o dia todo.

COMO RODAR
  python focus_brief.py          (uma vez)
  Windows: py focus_brief.py
  Loop (atualiza sozinho): rodar_loop.bat

Requisitos: apenas Python 3.9+
"""

import calendar
import csv
import io
import json
import os
import sys
import sqlite3
import datetime as dt
import urllib.request
import urllib.parse

# ----------------------------------------------------------------------------
# CONFIGURACAO
# ----------------------------------------------------------------------------

IBGE_CAL_URL = "https://servicodados.ibge.gov.br/api/v3/calendario/"
AGENDA_DIAS = 21  # janela: proximos N dias
REFRESH_SEG = 1800  # auto-refresh do HTML (segundos). 1800 = 30 min.

# COPOM (decisao de Selic) — datas OFICIAIS 2026. Atualize 1x/ano.
COPOM_2026 = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-08-05", "2026-09-16", "2026-11-04", "2026-12-09",
]

# FOMC (decisao de juros dos EUA) — datas OFICIAIS 2026 (2o dia da reuniao).
FOMC_2026 = [
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]

# Series do BCB (SGS) para valores REALIZADOS — API gratis, sem chave.
SGS_SERIES = [
    ("Selic meta (% a.a.)", 432),
    ("IPCA no mês (%)", 433),
    ("IPCA acum. 12m (%)", 13522),
    ("Dólar venda (R$)", 1),
    ("IGP-M no mês (%)", 189),
]
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.%d/dados/ultimos/1?formato=json"

# Cotacoes ao vivo via stooq.com — CSV, sem chave. (nome, simbolo stooq)
STOOQ = [
    ("Ibovespa", "^bvp"),
    ("Dólar (USD/BRL)", "usdbrl"),
    ("S&P 500", "^spx"),
    ("Nasdaq", "^ndq"),
    ("Petróleo WTI", "cl.f"),
    ("Ouro", "gc.f"),
]
STOOQ_URL = "https://stooq.com/q/l/?s=%s&f=sd2t2ohlc&h&e=csv"

# Índices que mais movem o humor global — Ásia (fecha de madrugada, horário BR)
# e Europa (abre de manhã). (nome, símbolo stooq, região)
MUNDO = [
    ("Nikkei 225 🇯🇵", "^nkx", "Ásia"),
    ("Hang Seng 🇭🇰", "^hsi", "Ásia"),
    ("Shanghai 🇨🇳", "^shc", "Ásia"),
    ("KOSPI 🇰🇷", "^kospi", "Ásia"),
    ("DAX 🇩🇪", "^dax", "Europa"),
    ("FTSE 100 🇬🇧", "^ukx", "Europa"),
    ("CAC 40 🇫🇷", "^cac", "Europa"),
    ("Euro Stoxx 50 🇪🇺", "^stx", "Europa"),
    ("IBEX 35 🇪🇸", "^ibex", "Europa"),
]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "focus_hist.db")

INDICADORES = [
    "IPCA", "PIB Total", "Câmbio", "Selic", "IGP-M",
    "IPCA Administrados", "Conta corrente", "Balança comercial",
]

# Mapa: serie realizada (SGS) -> indicador do Focus (p/ leitura automatica)
REAL_TO_FOCUS = {
    "Selic meta (% a.a.)": "Selic",
    "IPCA acum. 12m (%)": "IPCA",
    "Dólar venda (R$)": "Câmbio",
}

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BCB_URL = ("https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/"
           "odata/ExpectativasMercadoAnuais")


# ----------------------------------------------------------------------------
# UTIL
# ----------------------------------------------------------------------------

def _log(msg):
    try:
        with open(os.path.join(OUT_DIR, "focus_debug.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (dt.datetime.now().isoformat(), msg))
    except Exception:
        pass


def _get_bytes(url, timeout=45):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (focus-brief)",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = (r.headers.get("Content-Encoding") or "").lower()
        if "gzip" in enc or raw[:2] == b"\x1f\x8b":
            import gzip as _gz
            raw = _gz.decompress(raw)
        elif "deflate" in enc:
            import zlib as _zl
            try:
                raw = _zl.decompress(raw)
            except _zl.error:
                raw = _zl.decompress(raw, -_zl.MAX_WBITS)
        return raw


def _get_json(url):
    return json.loads(_get_bytes(url).decode("utf-8"))


def _nth_last_business_day(year, month, n):
    """N-esimo ultimo dia util do mes (n=1 -> ultimo)."""
    last = calendar.monthrange(year, month)[1]
    uteis = [d for d in range(last, 0, -1)
             if dt.date(year, month, d).weekday() < 5]
    return dt.date(year, month, uteis[n - 1]) if len(uteis) >= n else None


# ----------------------------------------------------------------------------
# COLETA — FOCUS / BCB
# ----------------------------------------------------------------------------

def pegar_focus():
    hoje = dt.date.today()
    inicio = (hoje - dt.timedelta(days=30)).isoformat()
    filtro = urllib.parse.quote("Data ge '%s'" % inicio, safe="'")
    orderby = urllib.parse.quote("Data desc")
    select = ("Indicador,IndicadorDetalhe,Data,DataReferencia,"
              "Media,Mediana,Minimo,Maximo,numeroRespondentes")
    url = (BCB_URL + "?$top=2000&$format=json"
           "&$filter=" + filtro + "&$orderby=" + orderby + "&$select=" + select)
    _log("GET " + url)
    dados = _get_json(url)["value"]
    _log("recebidos %d registros" % len(dados))
    melhor = {}
    for r in dados:
        ind = r.get("Indicador", "").strip()
        if ind not in INDICADORES:
            continue
        if r.get("IndicadorDetalhe"):
            continue
        chave = (ind, r.get("DataReferencia"))
        if chave not in melhor or r["Data"] > melhor[chave]["Data"]:
            melhor[chave] = r
    return melhor


def pegar_sgs():
    out = []
    for nome, cod in SGS_SERIES:
        try:
            dados = _get_json(SGS_URL % cod)
            if dados:
                item = dados[-1]
                out.append({"nome": nome, "data": item.get("data", ""),
                            "valor": item.get("valor", "")})
        except Exception as e:
            _log("ERRO SGS %s (%d): %r" % (nome, cod, e))
    return out


# ----------------------------------------------------------------------------
# COLETA — COTACOES AO VIVO (stooq)
# ----------------------------------------------------------------------------

def pegar_cotacoes():
    """Ibovespa, dolar, indices, commodities via stooq.com (CSV gratis)."""
    out = []
    for nome, simb in STOOQ:
        try:
            txt = _get_bytes(STOOQ_URL % urllib.parse.quote(simb), timeout=20).decode("utf-8")
            rows = list(csv.DictReader(io.StringIO(txt)))
            if not rows:
                continue
            r = rows[0]
            close = r.get("Close") or r.get("close")
            openp = r.get("Open") or r.get("open")
            if close in (None, "", "N/D"):
                continue
            c = float(close)
            var = ""
            try:
                o = float(openp)
                if o:
                    pct = (c - o) / o * 100.0
                    seta = "▲" if pct > 0 else ("▼" if pct < 0 else "▬")
                    var = ("%s %+.2f%%" % (seta, pct)).replace(".", ",")
            except (TypeError, ValueError):
                pass
            out.append({"nome": nome, "valor": c, "var": var,
                        "hora": (r.get("Time") or "")[:5]})
        except Exception as e:
            _log("ERRO stooq %s (%s): %r" % (nome, simb, e))
    return out


def pegar_indices_mundo():
    """Índices de Ásia e Europa via stooq (CSV grátis). Defensivo: se um
    símbolo falhar ou vier sem dado, é ignorado — nunca quebra o brief."""
    out = []
    for nome, simb, regiao in MUNDO:
        try:
            txt = _get_bytes(STOOQ_URL % urllib.parse.quote(simb), timeout=20).decode("utf-8")
            rows = list(csv.DictReader(io.StringIO(txt)))
            if not rows:
                continue
            r = rows[0]
            close = r.get("Close") or r.get("close")
            openp = r.get("Open") or r.get("open")
            if close in (None, "", "N/D"):
                continue
            c = float(close)
            var = ""
            try:
                o = float(openp)
                if o:
                    pct = (c - o) / o * 100.0
                    seta = "▲" if pct > 0 else ("▼" if pct < 0 else "▬")
                    var = ("%s %+.2f%%" % (seta, pct)).replace(".", ",")
            except (TypeError, ValueError):
                pass
            out.append({"nome": nome, "valor": c, "var": var,
                        "hora": (r.get("Time") or "")[:5], "regiao": regiao})
        except Exception as e:
            _log("ERRO stooq mundo %s (%s): %r" % (nome, simb, e))
    return out


# ----------------------------------------------------------------------------
# COLETA — AGENDA (IBGE + Copom + FOMC + Banco Central)
# ----------------------------------------------------------------------------

# Palavras-chave dos indicadores que mais importam (amplo p/ nao perder releases).
_AGENDA_CHAVES = [
    "ipca", "inpc", "igp", "preço", "preco", "consumidor", "inflaç", "inflac",
    "pib", "conta", "produto interno", "produç", "produc", "indústria", "industria",
    "industrial", "varejo", "comérc", "comerc", "serviç", "servic",
    "desemprego", "pnad", "emprego", "renda", "ocupaç", "ocupac",
    "custo", "construç", "construc", "atacado",
]


def _parse_data_ibge(s):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = dt.datetime.strptime(s, fmt)
            hora = "" if d.hour == 0 and d.minute == 0 else d.strftime(" %H:%M")
            return d.date(), d.strftime("%d/%m/%Y") + hora
        except ValueError:
            continue
    return None, s


def _releases_bcb(hoje, ate):
    """Divulgacoes recorrentes do Banco Central (previstas, aprox.).
    Setor Externo (Transacoes Correntes + IDP) ~ 4o ultimo dia util do mes, 08:30."""
    ev = []
    ym = []
    y, m = hoje.year, hoje.month
    for _ in range(3):  # mes atual + 2 seguintes
        ym.append((y, m))
        m += 1
        if m > 12:
            m = 1; y += 1
    for (yy, mm) in ym:
        d = _nth_last_business_day(yy, mm, 4)  # heuristica: 4o ultimo dia util
        if d and hoje <= d <= ate:
            ev.append({"date": d, "quando": d.strftime("%d/%m/%Y") + " 08:30 (previsto)",
                       "evento": "🇧🇷 Setor Externo — Transações Correntes e IDP (BCB)",
                       "fonte": "BCB"})
    return ev


def pegar_agenda(dias=AGENDA_DIAS):
    hoje = dt.date.today()
    ate = hoje + dt.timedelta(days=dias)
    url = ("%s?de=%s&ate=%s&qtd=200"
           % (IBGE_CAL_URL, hoje.strftime("%Y-%m-%d"), ate.strftime("%Y-%m-%d")))
    _log("GET agenda IBGE " + url)
    eventos = []
    try:
        resp = _get_json(url)
        itens = resp.get("items", []) if isinstance(resp, dict) else (resp or [])
        _log("agenda IBGE: %d itens" % len(itens))
        for it in itens:
            titulo = (it.get("titulo") or it.get("produto") or "").strip()
            if not any(k in titulo.lower() for k in _AGENDA_CHAVES):
                continue
            d, txt = _parse_data_ibge(it.get("data_divulgacao") or it.get("data"))
            if d is None or d < hoje or d > ate:
                continue
            eventos.append({"date": d, "quando": txt, "evento": titulo, "fonte": "IBGE"})
    except Exception as e:
        print("Aviso: falha ao buscar agenda do IBGE:", e, file=sys.stderr)
        _log("ERRO agenda IBGE: %r" % e)

    # Banco Central — Setor Externo (Transacoes Correntes + IDP)
    try:
        eventos.extend(_releases_bcb(hoje, ate))
    except Exception as e:
        _log("ERRO releases BCB: %r" % e)

    for ds in COPOM_2026:
        try:
            d = dt.datetime.strptime(ds, "%Y-%m-%d").date()
        except ValueError:
            continue
        if hoje <= d <= ate:
            eventos.append({"date": d, "quando": d.strftime("%d/%m/%Y"),
                            "evento": "🇧🇷 Decisão de juros — Copom (Selic)", "fonte": "BCB"})

    for ds in FOMC_2026:
        try:
            d = dt.datetime.strptime(ds, "%Y-%m-%d").date()
        except ValueError:
            continue
        if hoje <= d <= ate:
            eventos.append({"date": d, "quando": d.strftime("%d/%m/%Y") + " 16:00",
                            "evento": "🇺🇸 Decisão de juros — FOMC (Fed)", "fonte": "Fed"})

    eventos.sort(key=lambda e: e["date"])
    return eventos


# ----------------------------------------------------------------------------
# HISTORICO (SQLite)
# ----------------------------------------------------------------------------

def hist_conectar():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS focus_hist("
                "data_coleta TEXT, indicador TEXT, ano TEXT, mediana REAL, "
                "PRIMARY KEY(data_coleta, indicador, ano))")
    return con


def variacao_desde_ultima(focus, con):
    ano = str(dt.date.today().year)
    hoje = dt.date.today().isoformat()
    prev = con.execute("SELECT MAX(data_coleta) FROM focus_hist "
                       "WHERE data_coleta < ?", (hoje,)).fetchone()[0]
    if not prev:
        return {}, None
    rows = con.execute("SELECT indicador, mediana FROM focus_hist "
                       "WHERE data_coleta=? AND ano=?", (prev, ano)).fetchall()
    prevmap = {i: v for i, v in rows}
    res = {}
    for ind in INDICADORES:
        atual = _focus_ano_corrente(ind, focus)
        if ind in prevmap and atual is not None:
            try:
                res[ind] = round(float(atual) - float(prevmap[ind]), 2)
            except (TypeError, ValueError):
                pass
    try:
        prev_fmt = dt.datetime.strptime(prev, "%Y-%m-%d").strftime("%d/%m")
    except ValueError:
        prev_fmt = prev
    return res, prev_fmt


def salvar_historico(focus, con):
    hoje = dt.date.today().isoformat()
    for (i, a), r in (focus or {}).items():
        m = r.get("Mediana")
        if m is not None:
            try:
                con.execute("INSERT OR REPLACE INTO focus_hist VALUES(?,?,?,?)",
                            (hoje, i, a, float(m)))
            except (TypeError, ValueError):
                pass
    con.commit()


# ----------------------------------------------------------------------------
# INTERPRETACAO
# ----------------------------------------------------------------------------

def _focus_ano_corrente(indicador, focus):
    ano = str(dt.date.today().year)
    for (i, a), r in (focus or {}).items():
        if i == indicador and a == ano:
            return r.get("Mediana")
    return None


def _leitura_realizado(nome, valor, focus):
    """LEITURA AUTOMATICA de um dado divulgado vs a projecao do Focus."""
    ind = REAL_TO_FOCUS.get(nome)
    if not ind:
        return "-"
    proj = _focus_ano_corrente(ind, focus)
    try:
        a = float(str(valor).replace(",", "."))
        e = float(proj)
    except (TypeError, ValueError):
        return "-"
    dif = a - e
    pe = ("%.2f" % e).replace(".", ",")
    if abs(dif) < 1e-9:
        return "em linha com o Focus (%s)" % pe
    acima = dif > 0
    if ind == "IPCA":
        return ("ACIMA da projeção Focus (%s) → pressão inflacionária, curva mais dura" % pe
                if acima else
                "ABAIXO da projeção Focus (%s) → inflação cedendo, favorável a corte" % pe)
    if ind == "Selic":
        return ("ACIMA do Focus (%s) → BC mais duro que o esperado" % pe
                if acima else
                "ABAIXO do Focus (%s) → BC mais brando que o esperado" % pe)
    if ind == "Câmbio":
        return ("real mais fraco que o projetado (Focus %s) → viés de inflação importada" % pe
                if acima else
                "real mais forte que o projetado (Focus %s) → alívio de câmbio" % pe)
    return "acima do Focus (%s)" % pe if acima else "abaixo do Focus (%s)" % pe


def _expectativa_focus(titulo, focus):
    t = titulo.lower()
    if "fomc" in t or "fed" in t:
        return "-"
    if "copom" in t or "selic" in t or ("juros" in t and "eua" not in t):
        v = _focus_ano_corrente("Selic", focus)
        return ("Selic esperada: %s%% a.a." % fmt(v)) if v is not None else "-"
    if "ipca" in t or "inpc" in t or "consumidor" in t or "inflaç" in t or "inflac" in t:
        v = _focus_ano_corrente("IPCA", focus)
        return ("IPCA ano: %s%%" % fmt(v)) if v is not None else "-"
    if "pib" in t or "produto interno" in t:
        v = _focus_ano_corrente("PIB Total", focus)
        return ("PIB ano: %s%%" % fmt(v)) if v is not None else "-"
    if "igp" in t:
        v = _focus_ano_corrente("IGP-M", focus)
        return ("IGP-M ano: %s%%" % fmt(v)) if v is not None else "-"
    if "conta" in t or "setor externo" in t or "corrente" in t:
        v = _focus_ano_corrente("Conta corrente", focus)
        return ("Conta corr. ano: US$ %s bi" % fmt(v)) if v is not None else "-"
    return "-"


def _o_que_observar(titulo):
    t = titulo.lower()
    if "fomc" in t or "fed" in t:
        return "Juros dos EUA: afeta dólar, fluxo p/ emergentes e bolsa brasileira."
    if "copom" in t or "selic" in t or ("juros" in t and "eua" not in t):
        return "Decisão e comunicado: tom mais duro ou mais brando move juros, câmbio e bolsa."
    if "ipca" in t or "inpc" in t or "consumidor" in t or "inflaç" in t or "inflac" in t:
        return "Acima do esperado → pressão de alta em juros/dólar; abaixo → alívio."
    if "pib" in t or "produto interno" in t:
        return "Acima → atividade forte; abaixo → viés de corte de juros."
    if "desemprego" in t or "pnad" in t or "emprego" in t or "ocupaç" in t or "ocupac" in t:
        return "Mercado de trabalho: forte pressiona juros; fraco alivia."
    if "conta" in t or "setor externo" in t or "corrente" in t:
        return "Contas externas: déficit maior pressiona o real; IDP firme dá suporte."
    if ("industr" in t or "varejo" in t or "comérc" in t or "comerc" in t
            or "serviç" in t or "servic" in t or "produç" in t or "produc" in t):
        return "Atividade setorial: sinaliza força da economia no trimestre."
    return "Divulgação oficial — comparar com o esperado."


def _delta_txt(v):
    if v is None:
        return ""
    if abs(v) < 0.005:
        return "▬"
    seta = "▲" if v > 0 else "▼"
    return ("%s %+.2f" % (seta, v)).replace(".", ",")


# ----------------------------------------------------------------------------
# RENDER
# ----------------------------------------------------------------------------

def fmt(v):
    if v is None:
        return "-"
    try:
        return ("%.2f" % float(v)).replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


def _fmt_cot(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if v >= 1000:
        return "{:,.0f}".format(v).replace(",", ".")
    return ("%.2f" % v).replace(".", ",")


def ler_parecer():
    """Le o parecer interpretado (parecer.md), escrito pela tarefa horaria."""
    p = os.path.join(OUT_DIR, "parecer.md")
    try:
        with open(p, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        return txt or None
    except Exception:
        return None


def montar_brief(focus, agenda, variacao=None, prev_fmt=None, sgs=None,
                 cotacoes=None, parecer=None, mundo=None):
    hoje = dt.date.today().strftime("%d/%m/%Y")
    agora = dt.datetime.now().strftime("%H:%M")
    variacao = variacao or {}
    L = []
    L.append("# Panorama de Mercado — %s\n" % hoje)
    L.append("_Atualizado às %s. Fontes: Focus/SGS/Copom/Setor Externo (BCB), "
             "agenda IBGE, FOMC (Fed), cotações stooq. Não é recomendação._\n" % agora)

    # ---- Parecer do dia (leitura interpretada) ----
    if parecer:
        L.append("## 📌 Parecer do dia — leitura interpretada\n")
        L.append(parecer + "\n")

    # ---- Cotacoes ao vivo ----
    if cotacoes:
        L.append("## Mercado agora (cotações)\n")
        L.append("| Ativo | Nível | No dia (vs abertura) |")
        L.append("|---|---|---|")
        for c in cotacoes:
            L.append("| %s | %s | %s |" % (c["nome"], _fmt_cot(c["valor"]),
                                           c.get("var") or "-"))
        L.append("\n_Cotações de fonte gratuita (stooq), com atraso; variação medida "
                 "vs. abertura do dia. Referência para leitura, não para execução._\n")

    # ---- Abertura das bolsas: Ásia e Europa ----
    if mundo:
        L.append("## 🌏 Abertura das bolsas — Ásia e Europa\n")
        L.append("_As bolsas que mais movem o humor global. A Ásia já fechou "
                 "(pregão de madrugada, horário de Brasília); a Europa abre pela "
                 "manhã. Fonte: stooq, com atraso._\n")
        for regiao, titulo in (("Ásia", "**Ásia** — fechamento"),
                               ("Europa", "**Europa** — abertura")):
            linhas = [m for m in mundo if m.get("regiao") == regiao]
            if not linhas:
                continue
            L.append(titulo + "\n")
            L.append("| Bolsa | Nível | No dia (vs abertura) |")
            L.append("|---|---|---|")
            for m in linhas:
                L.append("| %s | %s | %s |" % (m["nome"], _fmt_cot(m["valor"]),
                                               m.get("var") or "-"))
            L.append("")

    # ---- Focus ----
    L.append("## Expectativas de Mercado (Focus)\n")
    if focus:
        anos = sorted({k[1] for k in focus.keys()})
        ano_atual = str(dt.date.today().year)
        cab = "| Indicador | " + " | ".join(anos) + " |"
        if variacao:
            cab = cab + (" Δ %s (vs %s) |" % (ano_atual, prev_fmt or "-"))
        L.append(cab)
        L.append("|" + "---|" * (len(anos) + (2 if variacao else 1)))
        for ind in INDICADORES:
            linha = ["%s" % ind]
            achou = False
            for ano in anos:
                val = None
                for (i, a), r in focus.items():
                    if i == ind and a == ano:
                        val = r["Mediana"]; achou = True; break
                linha.append(fmt(val))
            if variacao:
                linha.append(_delta_txt(variacao.get(ind)).strip() or "-")
            if achou:
                L.append("| " + " | ".join(linha) + " |")
        nota = "_Valores = mediana das projecoes."
        if variacao:
            nota += (" Coluna Δ = variação da projeção do ano corrente desde a "
                     "coleta de %s (▲ subiu, ▼ caiu)." % (prev_fmt or "-"))
        L.append("\n" + nota + "_\n")
    else:
        L.append("_Nao foi possivel obter os dados do Focus agora._\n")

    # ---- Realizado recente (SGS) + leitura automatica ----
    if sgs:
        L.append("## Realizado recente (divulgado) — leitura automática vs Focus\n")
        L.append("| Indicador | Último valor | Data | Leitura (vs Focus) |")
        L.append("|---|---|---|---|")
        for s in sgs:
            leitura = _leitura_realizado(s["nome"], s["valor"], focus)
            L.append("| %s | %s | %s | %s |" % (
                s["nome"], str(s["valor"]).replace(".", ","), s["data"], leitura))
        L.append("\n_A coluna Leitura compara o número divulgado com a projeção do "
                 "Focus para o ano — é o \"não operar no escuro\": mostra se o dado "
                 "veio acima (pressão) ou abaixo (alívio) do esperado._\n")

    # ---- Agenda ----
    L.append("## Agenda económica (próximos %d dias)\n" % AGENDA_DIAS)
    if not agenda:
        L.append("_Sem eventos relevantes no periodo._\n")
    else:
        L.append("| Quando | Evento | Expectativa (Focus) | O que observar |")
        L.append("|---|---|---|---|")
        for e in agenda:
            exp = _expectativa_focus(e["evento"], focus)
            obs = _o_que_observar(e["evento"])
            L.append("| %s | %s | %s | %s |" % (
                e.get("quando", "-"), e.get("evento", "-"), exp, obs))
        L.append("\n_Compare o número divulgado com a Expectativa: acima = pressão de "
                 "alta; abaixo = alívio. Eventos do BCB marcados \"previsto\" usam data "
                 "estimada (confirme no site do Banco Central)._\n")

    L.append("---")
    L.append("_Gerado automaticamente em %s. Não é recomendação de investimento._"
             % dt.datetime.now().strftime("%d/%m/%Y %H:%M"))
    return "\n".join(L)


def md_para_html(md, auto_refresh=True):
    linhas = md.split("\n")
    head = ["<!doctype html><meta charset='utf-8'>"]
    if auto_refresh:
        head.append("<meta http-equiv='refresh' content='%d'>" % REFRESH_SEG)
    head.append(
        "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;"
        "margin:24px auto;padding:0 16px;color:#1a1a1a}"
        "table{border-collapse:collapse;width:100%;margin:12px 0}"
        "th,td{border:1px solid #ddd;padding:6px 10px;font-size:14px;text-align:left}"
        "th{background:#f4f6f8}h1{font-size:24px}h2{font-size:18px;margin-top:28px}"
        "code,em{color:#555}</style>")
    html = head[:]
    in_tbl = False
    for ln in linhas:
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if set("".join(cells)) <= set("-| "):
                continue
            if not in_tbl:
                html.append("<table>"); in_tbl = True
                html.append("<tr>" + "".join("<th>%s</th>" % c for c in cells) + "</tr>")
            else:
                html.append("<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>")
        else:
            if in_tbl:
                html.append("</table>"); in_tbl = False
            if ln.startswith("# "):
                html.append("<h1>%s</h1>" % ln[2:])
            elif ln.startswith("## "):
                html.append("<h2>%s</h2>" % ln[3:])
            elif ln.startswith("---"):
                html.append("<hr>")
            elif ln.strip():
                import re as _re
                s = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", ln)
                html.append("<p>%s</p>" % s.replace("_", ""))
    if in_tbl:
        html.append("</table>")
    return "\n".join(html)


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    print("Coletando Focus (BCB)...")
    try:
        focus = pegar_focus()
    except Exception as e:
        print("Erro ao buscar Focus:", e, file=sys.stderr)
        _log("ERRO Focus: %r" % e)
        focus = {}

    print("Coletando cotações (stooq)...")
    try:
        cotacoes = pegar_cotacoes()
    except Exception as e:
        _log("ERRO cotacoes: %r" % e)
        cotacoes = []

    print("Coletando índices de Ásia/Europa (stooq)...")
    try:
        mundo = pegar_indices_mundo()
    except Exception as e:
        _log("ERRO indices mundo: %r" % e)
        mundo = []

    print("Coletando agenda económica...")
    agenda = pegar_agenda()

    print("Coletando valores realizados (SGS)...")
    try:
        sgs = pegar_sgs()
    except Exception as e:
        _log("ERRO SGS: %r" % e)
        sgs = []

    variacao, prev_fmt = {}, None
    try:
        con = hist_conectar()
        variacao, prev_fmt = variacao_desde_ultima(focus, con)
        salvar_historico(focus, con)
        con.close()
    except Exception as e:
        _log("ERRO historico: %r" % e)

    parecer = ler_parecer()
    md = montar_brief(focus, agenda, variacao, prev_fmt, sgs, cotacoes, parecer, mundo)
    stamp = dt.date.today().isoformat()
    # gera apenas os arquivos datados do dia (o HTML se recarrega sozinho a cada 30 min)
    paths = {
        os.path.join(OUT_DIR, "brief_%s.md" % stamp): ("md", False),
        os.path.join(OUT_DIR, "brief_%s.html" % stamp): ("html", True),
    }
    for path, (kind, refresh) in paths.items():
        content = md if kind == "md" else md_para_html(md, auto_refresh=refresh)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    print("\nBrief gerado: brief_%s.html (recarrega sozinho a cada 30 min)." % stamp)


if __name__ == "__main__":
    main()
