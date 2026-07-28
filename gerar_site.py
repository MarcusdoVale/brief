#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_site.py — gera o index.html do site a partir do focus_brief.py.

Reusa exatamente as mesmas fontes gratuitas do focus_brief.py (Focus/BCB,
cotacoes stooq, agenda IBGE, Copom/FOMC) e escreve UM index.html (a pagina
inicial do site). Roda tanto no seu PC quanto na nuvem (GitHub Actions).

Uso:
    python gerar_site.py
"""
import os
import datetime as dt

import focus_brief as fb

OUT = os.path.dirname(os.path.abspath(__file__))


def _titulo_html(html):
    """Coloca um <title> amigavel na pagina."""
    hoje = dt.date.today().strftime("%d/%m/%Y")
    title = "<title>Brief de Mercado — %s</title>" % hoje
    return html.replace("<meta charset='utf-8'>",
                        "<meta charset='utf-8'>\n" + title, 1)


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
    html = _titulo_html(fb.md_para_html(md, auto_refresh=True))

    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html gerado em", OUT)


if __name__ == "__main__":
    main()
