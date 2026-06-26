import json
import math
from typing import Any


def _bar_chart(data: list[dict[str, Any]], label_key: str, value_key: str,
               width: int = 600, height: int = 200, color: str = "#3B82F6",
               max_val: float | None = None) -> str:
    if not data:
        return '<p style="color:#999">Sem dados</p>'

    values = [d[value_key] for d in data]
    mv = max_val or max(values) or 1
    bar_w = max(8, (width - 40) // len(data) - 4)
    chart_h = height - 30

    bars = ""
    for i, d in enumerate(data):
        bar_h = max(3, (d[value_key] / mv) * chart_h)
        x = 20 + i * (bar_w + 4)
        y = chart_h - bar_h + 5
        label = str(d[label_key])[:6]
        bars += f"""
        <g>
            <rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" rx="3" fill="{color}" opacity="0.85">
                <title>{label}: {d[value_key]:,.2f}</title>
            </rect>
            <text x="{x + bar_w/2}" y="{chart_h + 18}" text-anchor="middle" font-size="10" fill="#888">{label}</text>
        </g>"""

    return f"""
    <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
        <line x1="15" y1="5" x2="15" y2="{chart_h + 5}" stroke="#e2e8f0" stroke-width="1"/>
        <line x1="15" y1="{chart_h + 5}" x2="{width - 5}" y2="{chart_h + 5}" stroke="#e2e8f0" stroke-width="1"/>
        {bars}
    </svg>"""


def _metric_card(label: str, value: str, sub: str = "", color: str = "#3B82F6",
                 icon: str = "📊") -> str:
    return f"""
    <div style="background:#fff; border-radius:10px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,.06);
                border-left:3px solid {color}">
        <div style="font-size:18px; margin-bottom:4px">{icon}</div>
        <div style="font-size:10px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.3px">{label}</div>
        <div style="font-size:18px; font-weight:700; color:#1a1a2e; margin:2px 0; white-space:nowrap">{value}</div>
        <div style="font-size:11px; color:#aaa; white-space:nowrap; overflow:hidden; text-overflow:ellipsis">{sub}</div>
    </div>"""


def _section(title: str, content: str, icon: str = "") -> str:
    return f"""
    <div style="background:#fff; border-radius:14px; padding:28px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,.06)">
        <h2 style="margin:0 0 20px; font-size:18px; color:#1a1a2e; border-bottom:2px solid #3B82F6; padding-bottom:10px">
            {icon} {title}
        </h2>
        {content}
    </div>"""


def _table(headers: list[str], rows: list[list[str]], highlight_col: int = -1) -> str:
    thead = "".join(f'<th style="padding:10px 14px; text-align:left; border-bottom:2px solid #e2e8f0; font-size:11px; color:#888; text-transform:uppercase">{h}</th>' for h in headers)
    tbody = ""
    for row in rows:
        cells = ""
        for i, cell in enumerate(row):
            style = "padding:10px 14px; border-bottom:1px solid #f1f5f9; font-size:13px;"
            if i == highlight_col:
                style += "font-weight:700; color:#3B82F6"
            cells += f'<td style="{style}">{cell}</td>'
        tbody += f"<tr>{cells}</tr>"

    return f"""
    <div style="overflow-x:auto">
    <table style="width:100%; border-collapse:collapse">
        <thead><tr>{thead}</tr></thead>
        <tbody>{tbody}</tbody>
    </table>
    </div>"""


def _progress_bar(value: float, max_val: float, label: str, color: str = "#3B82F6") -> str:
    pct = min(100, (value / max_val * 100)) if max_val > 0 else 0
    return f"""
    <div style="margin:8px 0">
        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px">
            <span style="color:#555">{label}</span>
            <span style="font-weight:600; color:{color}">{value:,.1f}</span>
        </div>
        <div style="background:#f1f5f9; border-radius:6px; height:8px">
            <div style="background:{color}; width:{pct}%; height:100%; border-radius:6px; transition:width .3s"></div>
        </div>
    </div>"""


def gerar_relatorio_html(resultado: dict, caminho_saida: str = "relatorio_financeiro.html") -> str:
    calc = resultado.get("calculos_financeiros", {})
    resumo = calc.get("resumo_executivo", {})
    projeto = resultado.get("analise_projeto", {})
    risco = resultado.get("matriz_risco", {})
    custos = resultado.get("custos_infraestrutura", {})

    inv = calc.get("investimento_inicial", {})
    semantica = resultado.get("analise_semantica", {})
    projeto_pronto = inv.get("projeto_pronto", True)
    total_linhas = projeto.get("total_linhas", 0)
    inv_dev_label = "Desenvolvimento (já executado)" if projeto_pronto else "Desenvolvimento (2.000h)"
    inv_dev_row = [inv_dev_label, f"R$ {inv.get('desenvolvimento_sunk', inv.get('desenvolvimento', 0)):,.0f}",
                   f"{inv.get('desenvolvimento_sunk', inv.get('desenvolvimento', 0)) / (inv.get('total', 0) + inv.get('desenvolvimento_sunk', 0)) * 100:.0f}%",
                   f"{total_linhas:,} linhas de código · já concluído" if projeto_pronto else "Equipe de 2 devs fullstack"]
    prec = calc.get("precificacao", {})
    pe = calc.get("ponto_equilibrio", {})
    pb = calc.get("payback", {})
    pb5 = pb.get("5_clientes", {})
    pb50 = pb.get("50_clientes", {})
    vpl_tir = calc.get("vpl_tir", {})
    perf = calc.get("performance", {})
    met = calc.get("metricas_cliente", {})
    proj = calc.get("projecao_12_meses", [])

    # Build risk level styling
    risco_score = resumo.get("score_risco", 0)
    risco_score_100 = round(risco_score * 10)  # 0-10 → 0-100
    risco_pct = risco_score_100  # 0-100 for the gauge arc

    # Serasa-style color zones (0-100 scale)
    if risco_score_100 <= 30:
        risco_color = "#22C55E"; risco_label = "BAIXO"; risco_zone = "verde"
    elif risco_score_100 <= 50:
        risco_color = "#84CC16"; risco_label = "MODERADO"; risco_zone = "amarelo"
    elif risco_score_100 <= 70:
        risco_color = "#EAB308"; risco_label = "ATENÇÃO"; risco_zone = "laranja"
    else:
        risco_color = "#EF4444"; risco_label = "ALTO"; risco_zone = "vermelho"

    # Gauge constants
    gauge_cx, gauge_cy, gauge_r = 140, 110, 90
    start_angle = -180  # left
    end_angle = 0       # right
    total_arc = 180

    def polar_to_cartesian(cx, cy, r, angle_deg):
        rad = math.radians(angle_deg)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    # Colored arcs (3 zones: green 0-40, yellow 40-70, red 70-100)
    def arc_path(cx, cy, r, start, end):
        x1, y1 = polar_to_cartesian(cx, cy, r, start)
        x2, y2 = polar_to_cartesian(cx, cy, r, end)
        large = 1 if (end - start) > 90 else 0
        return f"M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}"

    arc_green = arc_path(gauge_cx, gauge_cy, gauge_r - 18, start_angle, start_angle + total_arc * 0.40)
    arc_yellow = arc_path(gauge_cx, gauge_cy, gauge_r - 18, start_angle + total_arc * 0.40, start_angle + total_arc * 0.70)
    arc_red = arc_path(gauge_cx, gauge_cy, gauge_r - 18, start_angle + total_arc * 0.70, end_angle)

    # Needle angle
    needle_angle = start_angle + (risco_pct / 100) * total_arc
    needle_len = gauge_r - 24
    nx, ny = polar_to_cartesian(gauge_cx, gauge_cy, needle_len, needle_angle)
    risco_bg = "rgba(34,197,94,0.06)" if risco_score_100 <= 30 else "rgba(234,179,8,0.06)" if risco_score_100 <= 70 else "rgba(239,68,68,0.06)"

    # Hero gauge
    hero_disk = f"""
    <div style="display:flex; align-items:center; gap:10px; flex-shrink:0">
        <div style="position:relative; width:300px; height:160px; flex-shrink:0">
            <svg width="300" height="160" viewBox="0 0 300 160">
                <defs>
                    <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
                    <filter id="needleShadow"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity="0.3"/></filter>
                </defs>
                <!-- Background track -->
                <path d="{arc_path(gauge_cx, gauge_cy, gauge_r - 18, start_angle, end_angle)}" fill="none" stroke="#e2e8f0" stroke-width="16" stroke-linecap="round"/>
                <!-- Green zone 0-40 -->
                <path d="{arc_green}" fill="none" stroke="#22C55E" stroke-width="16" stroke-linecap="butt"/>
                <!-- Yellow zone 40-70 -->
                <path d="{arc_yellow}" fill="none" stroke="#EAB308" stroke-width="16" stroke-linecap="butt"/>
                <!-- Red zone 70-100 -->
                <path d="{arc_red}" fill="none" stroke="#EF4444" stroke-width="16" stroke-linecap="butt"/>
                <!-- Needle -->
                <line x1="{gauge_cx:.0f}" y1="{gauge_cy:.0f}" x2="{nx:.0f}" y2="{ny:.0f}"
                      stroke="#1a1a2e" stroke-width="2.5" stroke-linecap="round" filter="url(#needleShadow)"/>
                <circle cx="{gauge_cx:.0f}" cy="{gauge_cy:.0f}" r="7" fill="#1a1a2e"/>
                <circle cx="{gauge_cx:.0f}" cy="{gauge_cy:.0f}" r="3.5" fill="#fff"/>
                <!-- Score text -->
                <text x="{gauge_cx:.0f}" y="{gauge_cy + 28:.0f}" text-anchor="middle" font-size="28" font-weight="800" fill="{risco_color}">{risco_score_100}</text>
                <text x="{gauge_cx:.0f}" y="{gauge_cy + 42:.0f}" text-anchor="middle" font-size="10" fill="#64748b">de 100</text>
                <!-- Labels -->
                <text x="55" y="135" text-anchor="middle" font-size="10" fill="#94a3b8">0</text>
                <text x="245" y="135" text-anchor="middle" font-size="10" fill="#94a3b8">100</text>
            </svg>
        </div>
        <div style="min-width:120px">
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:1.5px; color:{risco_color}; margin-bottom:4px">Score de Risco</div>
            <div style="font-size:15px; font-weight:700; color:#fff">{risco_label}</div>
            <div style="font-size:11px; color:#94a3b8; margin-top:3px; max-width:180px">{risco.get('score_global', {}).get('parecer', '')}</div>
        </div>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatório de Validação de Negócio — {projeto.get('nome', 'Projeto')}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box }}
body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #f8fafc; color: #334155; line-height:1.5 }}
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 30px 50px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:20px }}
.header-left h1 {{ font-size: 26px; font-weight: 700; line-height:1.2 }}
.header-left p {{ opacity: 0.6; margin-top: 4px; font-size: 13px }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 24px }}
.metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 20px }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px }}
.chart-box {{ background:#f8fafc; border-radius:10px; padding:16px; text-align:center }}
.tag {{ display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600 }}
.footer {{ text-align:center; padding:30px; color:#94a3b8; font-size:12px }}
.risk-hero-disk svg {{ filter: drop-shadow(0 0 10px {risco_color}30); }}
@media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr }} .header {{ padding: 20px }} }}
</style>
</head>
<body>

<div class="header">
    <div class="header-left">
        <h1>📊 Relatório de Validação de Negócio</h1>
        <p>{projeto.get('nome', 'Projeto')} — {semantica.get('tipo_produto', 'Software')} · {semantica.get('nicho', '')}</p>
        <p style="font-size:11px; opacity:0.4; margin-top: 2px">Análise automática · Dados reais de mercado · Cálculos matemáticos</p>
    </div>
    <div class="risk-hero-disk">
        {hero_disk}
    </div>
</div>

<div class="container">

<!-- EXECUTIVE SUMMARY -->
<div style="background:#fff; border-radius:14px; padding:28px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,.06)">
    <h2 style="margin:0 0 16px; font-size:18px; color:#1a1a2e">📋 Resumo Executivo</h2>
    <div class="metrics-grid" style="grid-template-columns: repeat(6, 1fr); gap:10px">
        {_metric_card("Investimento", f"R$ {inv.get('total', 0):,.0f}", f"Payback: {pb5.get('meses', '?')} meses", "#8B5CF6", "💰")}
        {_metric_card("Custo Mensal", f"R$ {resumo.get('custo_mensal', 0):,.0f}", "Infra + serviços", "#F59E0B", "🏗️")}
        {_metric_card("Break-even", f"{pe.get('clientes_necessarios', '?')} clientes", f"R$ {pe.get('faturamento_minimo_mensal', 0):,.0f}", "#10B981", "🎯")}
        {_metric_card("Lucro Ano 1", f"R$ {perf.get('lucro_liquido', 0):,.0f}", f"{perf.get('margem_liquida', 0)}% margem", "#3B82F6", "📈")}
        {_metric_card("LTV/CAC", f"{met.get('razao_ltv_cac', 0)}:1", met.get('ltv_cac_interpretacao', ''), "#EC4899", "👥")}
        {_metric_card("VPL (5a)", f"R$ {vpl_tir.get('vpl', 0):,.0f}", f"TIR {vpl_tir.get('tir', 0)}%", "#8B5CF6", "💵")}
    </div>
</div>

<!-- 1. INVESTIMENTO INICIAL -->
{_section("💡 1. Planejamento e Investimento Inicial", f'''
{_table(
    ["Componente", "Valor", "% do Total", "Detalhe"],
    [
        inv_dev_row,
        ["Investimento Fixo", f"R$ {inv.get('fixo', 0):,.0f}", f"{inv.get('fixo', 0) / (inv.get('total', 0) + (0 if projeto_pronto else inv.get('desenvolvimento', 0)) or 1) * 100:.0f}%", "Computadores, móveis, equipamentos"],
        ["Gastos Pré-operacionais", f"R$ {inv.get('pre_operacionais', 0):,.0f}", f"{inv.get('pre_operacionais', 0) / (inv.get('total', 0) + (0 if projeto_pronto else inv.get('desenvolvimento', 0)) or 1) * 100:.0f}%", "CNPJ, contador, licenças, pesquisa"],
        [f"Capital de Giro ({inv.get('meses_capital_giro', 3)} meses)", f"R$ {inv.get('capital_giro', 0):,.2f}", f"{inv.get('capital_giro', 0) / (inv.get('total', 0) + (0 if projeto_pronto else inv.get('desenvolvimento', 0)) or 1) * 100:.0f}%", "Reserva para operação inicial"],
        ["TOTAL (go-to-market)", f"R$ {inv.get('total', 0):,.0f}", "—", "Investimento necessário para lançar" if projeto_pronto else "Investimento total incluindo desenvolvimento"],
    ],
    highlight_col=1
)}
<div style="margin-top:16px; background:#f0f9ff; padding:14px; border-radius:8px; font-size:13px; color:#0369a1">
    <strong>📌 Interpretação:</strong> {
    f"Projeto já desenvolvido ({projeto.get('total_linhas', 0):,} linhas). "
    f"Investimento go-to-market: R$ {inv.get('total', 0):,.0f} cobre abertura, infra e 3 meses de capital de giro."
    if projeto_pronto else
    f"Investimento total de R$ {inv.get('total', 0):,.0f} cobre desenvolvimento + 3 meses de operação."
    }
</div>
''')}

<!-- 2. PRECIFICAÇÃO -->
{_section("🏷️ 2. Precificação e Custos", f'''
<div class="two-col">
    <div>
        <h3 style="font-size:14px; margin-bottom:12px; color:#555">Estrutura de Custos Mensal</h3>
        {_progress_bar(prec.get('custo_fixo_total_mensal', 0), prec.get('preco_venda', 1) * 10, "Custo Fixo (infra + serviços)", "#F59E0B")}
        {_progress_bar(prec.get('custo_variavel_unitario', 0), prec.get('preco_venda', 1), "Custo Variável por Cliente", "#EF4444")}
        {_progress_bar(prec.get('margem_contribuicao', 0), prec.get('preco_venda', 1), "Margem de Contribuição", "#10B981")}
        <div style="margin-top:12px; font-size:13px; color:#555">
            <strong>Preço de Venda:</strong> R$ {prec.get('preco_venda', 0):,.2f}/mês<br>
            <strong>Markup:</strong> {prec.get('markup', 0)}×<br>
            <strong>Índice MC:</strong> {prec.get('indice_margem_contribuicao', 0)}%
        </div>
    </div>
    <div class="chart-box">
        <h3 style="font-size:14px; margin-bottom:8px; color:#555">Composição do Preço (R$ {prec.get('preco_venda', 0):,.2f})</h3>
        {_bar_chart(
            [{"item": "Custo Fixo", "valor": prec.get('custo_fixo_total_mensal', 0) / 10},
             {"item": "Custo Var", "valor": prec.get('custo_variavel_unitario', 0)},
             {"item": "Margem", "valor": prec.get('margem_contribuicao', 0)}],
            "item", "valor", width=400, height=180, color="#3B82F6", max_val=prec.get('preco_venda', 1)
        )}
    </div>
</div>
''')}

<!-- 3. VIABILIDADE -->
{_section("📈 3. Viabilidade e Ponto de Virada", f'''
<div class="two-col">
    <div>
        <h3 style="font-size:14px; margin-bottom:12px; color:#555">Ponto de Equilíbrio</h3>
        <div style="background:#f0fdf4; padding:16px; border-radius:10px">
            <div style="font-size:32px; font-weight:700; color:#10B981">{pe.get('clientes_necessarios', '?')}</div>
            <div style="font-size:13px; color:#555">clientes necessários</div>
            <div style="margin-top:6px; font-size:12px; color:#888">
                Faturamento mínimo: <strong>R$ {pe.get('faturamento_minimo_mensal', 0):,.2f}/mês</strong><br>
                Anual: R$ {pe.get('faturamento_minimo_anual', 0):,.2f}
            </div>
            <div style="margin-top:8px; font-size:11px; color:#aaa; font-style:italic">{pe.get('formula', '')}</div>
        </div>
    </div>
    <div>
        <h3 style="font-size:14px; margin-bottom:12px; color:#555">Payback (Retorno do Investimento)</h3>
        {_table(
            ["Cenário", "Lucro Mensal", "Payback", "Anos"],
            [
                ["5 clientes", f"R$ {pb5.get('lucro_mensal_estimado', 0):,.2f}", f"{pb5.get('meses', '?')} meses", f"{pb5.get('anos', '?')} anos"],
                ["50 clientes", f"R$ {pb50.get('lucro_mensal_estimado', 0):,.2f}", f"{pb50.get('meses', '?')} meses", f"{pb50.get('anos', '?')} anos"],
            ],
            highlight_col=2
        )}
    </div>
</div>
<div style="margin-top:20px">
    <h3 style="font-size:14px; margin-bottom:8px; color:#555">VPL e TIR (projeção 5 anos)</h3>
    <div class="metrics-grid">
        {_metric_card("VPL", f"R$ {vpl_tir.get('vpl', 0):,.0f}", vpl_tir.get('vpl_interpretacao', ''), "#10B981" if vpl_tir.get('vpl', 0) > 0 else "#EF4444", "💵")}
        {_metric_card("TIR", f"{vpl_tir.get('tir', 0)}% a.a.", vpl_tir.get('tir_interpretacao', ''), "#8B5CF6", "📊")}
        {_metric_card("Taxa Desconto", f"{vpl_tir.get('taxa_desconto', 0) * 100:.0f}% a.a.", "Selic + risco", "#F59E0B", "🏦")}
        {_metric_card("Fluxo Ano 5", f"R$ {vpl_tir.get('fluxos_anuais', [0]*5)[-1]:,.0f}", "Último ano da projeção", "#3B82F6", "📈")}
    </div>
</div>
''')}

<!-- 4. PERFORMANCE -->
{_section("💰 4. Performance e Lucratividade (Ano 1)", f'''
<div class="metrics-grid">
    {_metric_card("Faturamento Bruto", f"R$ {perf.get('faturamento_bruto', 0):,.2f}", "5 clientes × 12 meses", "#3B82F6", "💵")}
    {_metric_card("Custos Totais", f"R$ {perf.get('custo_fixo_total', 0) + perf.get('custo_variavel_total', 0):,.2f}", f"Fixo + Variável", "#F59E0B", "📉")}
    {_metric_card("Impostos", f"R$ {perf.get('impostos', 0):,.2f}", f"Simples Nacional (~{perf.get('impostos_percentual', 6)}%)", "#EF4444", "📋")}
    {_metric_card("Lucro Líquido", f"R$ {perf.get('lucro_liquido', 0):,.2f}", f"Margem: {perf.get('margem_liquida', 0)}%", "#10B981", "✅")}
    {_metric_card("ROI", f"{perf.get('roi', 0)}%", perf.get('roi_interpretacao', ''), "#8B5CF6", "🎯")}
</div>
<div style="margin-top:16px">
    {_bar_chart(
        [{"item": "Receita", "valor": perf.get('faturamento_bruto', 0)},
         {"item": "Custos", "valor": perf.get('custo_fixo_total', 0) + perf.get('custo_variavel_total', 0)},
         {"item": "Impostos", "valor": perf.get('impostos', 0)},
         {"item": "Lucro", "valor": perf.get('lucro_liquido', 0)}],
        "item", "valor", width=600, height=200, color="#3B82F6", max_val=perf.get('faturamento_bruto', 1)
    )}
    <p style="text-align:center; font-size:11px; color:#aaa; margin-top:4px">Demonstração de Resultados — Ano 1 (5 clientes)</p>
</div>
''')}

<!-- 5. METRICAS DE CLIENTES -->
{_section("👥 5. Métricas de Clientes (SaaS)", f'''
<div class="metrics-grid">
    {_metric_card("CAC", f"R$ {met.get('cac', 0):,.2f}", "Custo Aquisição Cliente", "#EC4899", "🎯")}
    {_metric_card("LTV", f"R$ {met.get('ltv', 0):,.2f}", f"{met.get('vida_media_meses', 0)} meses de vida", "#8B5CF6", "💎")}
    {_metric_card("LTV/CAC", f"{met.get('razao_ltv_cac', 0)}:1", met.get('ltv_cac_interpretacao', ''), "#10B981", "📊")}
    {_metric_card("Churn Rate", f"{met.get('churn_rate', 0)}%", met.get('churn_interpretacao', ''), "#F59E0B", "📉")}
</div>
<div style="margin-top:16px; background:#fefce8; padding:14px; border-radius:8px; font-size:13px; color:#92400e">
    <strong>📌 SaaS saudável:</strong> LTV/CAC {'>' if met.get('razao_ltv_cac', 0) > 3 else '<'} 3:1 e Churn {'<' if met.get('churn_rate', 0) < 5 else '>'} 5% ao mês.
    Cada cliente gera R$ {met.get('ltv', 0):,.2f} em {met.get('vida_media_meses', 0)} meses. O custo para adquiri-lo é R$ {met.get('cac', 0):,.2f}.
</div>
''')}

<!-- 6. PROJEÇÃO 12 MESES -->
{_section("📆 6. Projeção de Escala (12 meses: 5 → 50 clientes)", f'''
<div class="chart-box">
    {_bar_chart(
        [{"mes": f"M{d['mes']}", "lucro": d['lucro']} for d in proj],
        "mes", "lucro", width=700, height=220, color="#10B981",
        max_val=max((d['receita'] for d in proj), default=1)
    )}
    <p style="text-align:center; font-size:11px; color:#aaa; margin-top:4px">Lucro mensal projetado (R$) — {custos.get('escala', {}).get('clientes_inicial', 5)} → {custos.get('escala', {}).get('clientes_meta', 50)} clientes em 12 meses</p>
</div>
{_table(
    ["Mês", "Clientes", "Receita", "Custo Fixo", "Custo Var", "Lucro", "Lucro Acum."],
    [[f"M{d['mes']}", str(d['clientes']), f"R$ {d['receita']:,.0f}", f"R$ {d['custo_fixo']:,.0f}",
      f"R$ {d['custo_variavel']:,.0f}", f"R$ {d['lucro']:,.0f}", f"R$ {d['lucro_acumulado']:,.0f}"]
     for d in proj],
    highlight_col=5
)}
''')}

<!-- RISK MATRIX -->
{_section("🎯 7. Matriz de Risco de Mercado", f'''
<div style="background:{risco_bg}; border-radius:12px; padding:20px; margin-bottom:20px; text-align:center">
    <div style="font-size:13px; color:{risco_color}; font-weight:600; margin-bottom:6px">SCORE DE RISCO GLOBAL</div>
    <div style="font-size:48px; font-weight:800; color:{risco_color}; line-height:1">{risco_score_100}<span style="font-size:20px; opacity:0.5">/100</span></div>
    <div style="font-size:14px; color:#555; margin-top:4px">{risco_label}</div>
    <div style="font-size:12px; color:#888; margin-top:2px; max-width:400px; margin-left:auto; margin-right:auto">{risco.get('score_global', {}).get('parecer', '')}</div>
</div>
<div style="display:flex; gap:20px; flex-wrap:wrap">
    <div style="flex:1; min-width:200px">
        {_progress_bar(risco.get('risco_concorrencia', 0) * 10, 100, "Risco de Concorrência (30%)", "#F59E0B")}
        {_progress_bar(risco.get('risco_preco', {}).get('risco_preco', 0) * 10, 100, "Risco de Preço — Z-Score (30%)", "#EF4444")}
        {_progress_bar(0 if not risco.get('indice_hhi', {}).get('hhi') else min(100, risco['indice_hhi']['hhi'] / 10), 100, "Concentração de Mercado — HHI (25%)", "#8B5CF6")}
        {_progress_bar(0, 100, "Volatilidade de Preços (15%)", "#10B981")}
    </div>
</div>
''')}

</div>

<div class="footer">
    <p>Relatório gerado pelo Sistema de Validação Matemática de Ideias de Negócio</p>
    <p>Dados de mercado coletados via DuckDuckGo + páginas oficiais · Análise via DeepSeek · Cálculos financeiros com NumPy/SciPy</p>
</div>

</body>
</html>"""

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(html)

    return caminho_saida
