import math
import numpy as np


def calcular_investimento_inicial(infra_anual: float, dev_horas: int = 2000,
                                   valor_hora_dev: float = 80, legal: float = 5000,
                                   meses_capital_giro: int = 3, projeto_pronto: bool = True) -> dict:
    investimento_desenvolvimento = dev_horas * valor_hora_dev if not projeto_pronto else 0
    investimento_fixo = 15000 if not projeto_pronto else 3000  # Já tem equipamentos
    gastos_pre = legal  # CNPJ, contador, licenças
    custo_mensal = infra_anual / 12
    capital_giro = custo_mensal * meses_capital_giro

    total = investimento_desenvolvimento + investimento_fixo + gastos_pre + capital_giro

    return {
        "desenvolvimento": investimento_desenvolvimento,
        "desenvolvimento_sunk": dev_horas * valor_hora_dev,
        "fixo": investimento_fixo,
        "pre_operacionais": gastos_pre,
        "capital_giro": round(capital_giro, 2),
        "meses_capital_giro": meses_capital_giro,
        "total": round(total, 2),
        "projeto_pronto": projeto_pronto,
    }


def calcular_precificacao(preco_mensal: float, custo_fixo_mensal: float,
                           custo_variavel_por_cliente: float = 2.50,
                           custo_produto: float = 0) -> dict:
    markup = round(preco_mensal / custo_variavel_por_cliente, 2) if custo_variavel_por_cliente > 0 else 0
    margem_contribuicao = round(preco_mensal - custo_variavel_por_cliente, 2)

    return {
        "preco_venda": preco_mensal,
        "custo_fixo_total_mensal": custo_fixo_mensal,
        "custo_variavel_unitario": custo_variavel_por_cliente,
        "cmv_cpv": custo_produto,
        "markup": markup,
        "margem_contribuicao": margem_contribuicao,
        "indice_margem_contribuicao": round(margem_contribuicao / preco_mensal * 100, 1),
    }


def calcular_ponto_equilibrio(custo_fixo_mensal: float, preco: float,
                                custo_variavel: float) -> dict:
    margem = preco - custo_variavel
    qtd_clientes = math.ceil(custo_fixo_mensal / margem) if margem > 0 else float("inf")
    faturamento_min = round(qtd_clientes * preco, 2)

    return {
        "margem_contribuicao_unit": round(margem, 2),
        "clientes_necessarios": qtd_clientes,
        "faturamento_minimo_mensal": faturamento_min,
        "faturamento_minimo_anual": round(faturamento_min * 12, 2),
        "formula": f"R$ {custo_fixo_mensal} / (R$ {preco} - R$ {custo_variavel}) = {qtd_clientes} clientes",
    }


def calcular_payback(investimento_total: float, clientes: int, preco: float,
                      custo_fixo_mensal: float, custo_variavel_unit: float) -> dict:
    receita = clientes * preco
    lucro_mensal = receita - custo_fixo_mensal - (clientes * custo_variavel_unit)
    meses = math.ceil(investimento_total / lucro_mensal) if lucro_mensal > 0 else float("inf")

    return {
        "lucro_mensal_estimado": round(lucro_mensal, 2),
        "meses": meses,
        "anos": round(meses / 12, 1),
        "formula": f"R$ {investimento_total} / R$ {round(lucro_mensal, 2)} = {meses} meses",
    }


def calcular_vpl_tir(investimento: float, fluxos_anuais: list[float], taxa_desconto: float = 0.12) -> dict:
    vpl = -investimento
    for i, fluxo in enumerate(fluxos_anuais):
        vpl += fluxo / ((1 + taxa_desconto) ** (i + 1))
    vpl = round(vpl, 2)

    # TIR approximation via binary search
    tir = _calcular_tir(investimento, fluxos_anuais)

    return {
        "investimento": investimento,
        "fluxos_anuais": fluxos_anuais,
        "taxa_desconto": taxa_desconto,
        "vpl": vpl,
        "tir": round(tir * 100, 2),
        "vpl_interpretacao": "Viável (VPL > 0)" if vpl > 0 else "Inviável (VPL < 0)",
        "tir_interpretacao": f"Supera poupança (10.5% a.a.)" if tir > 0.105 else "Menor que poupança",
    }


def _calcular_tir(investimento: float, fluxos: list[float], max_iter: int = 1000) -> float:
    lo, hi = -0.99, 5.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        vpl = -investimento
        for i, f in enumerate(fluxos):
            vpl += f / ((1 + mid) ** (i + 1))
        if abs(vpl) < 0.01:
            return mid
        if vpl > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def calcular_performance(faturamento_bruto: float, custo_fixo_total: float,
                          custo_variavel_total: float = 0, impostos_percent: float = 6,
                          investimento: float = 0) -> dict:
    impostos = faturamento_bruto * (impostos_percent / 100)
    lucro_liquido = round(faturamento_bruto - custo_fixo_total - custo_variavel_total - impostos, 2)
    margem_liquida = round(lucro_liquido / faturamento_bruto * 100, 1) if faturamento_bruto > 0 else 0
    roi = round(lucro_liquido / investimento * 100, 1) if investimento > 0 else 0

    return {
        "faturamento_bruto": round(faturamento_bruto, 2),
        "custo_fixo_total": round(custo_fixo_total, 2),
        "custo_variavel_total": round(custo_variavel_total, 2),
        "impostos": round(impostos, 2),
        "impostos_percentual": impostos_percent,
        "lucro_liquido": lucro_liquido,
        "margem_liquida": margem_liquida,
        "roi": roi,
        "roi_interpretacao": "Excelente" if roi > 100 else "Bom" if roi > 50 else "Moderado" if roi > 20 else "Baixo",
    }


def calcular_metricas_cliente(clientes_atuais: int, novos_clientes_mes: int,
                                cancelados_mes: int, gasto_marketing_mensal: float,
                                receita_media_mes: float, vida_media_meses: int = 24) -> dict:
    cac = round(gasto_marketing_mensal / novos_clientes_mes, 2) if novos_clientes_mes > 0 else 0
    ltv = round(receita_media_mes * vida_media_meses, 2)
    churn = round(cancelados_mes / clientes_atuais * 100, 1) if clientes_atuais > 0 else 0
    razao_ltv_cac = round(ltv / cac, 1) if cac > 0 else 0

    return {
        "clientes_atuais": clientes_atuais,
        "novos_mes": novos_clientes_mes,
        "cancelados_mes": cancelados_mes,
        "cac": cac,
        "ltv": ltv,
        "vida_media_meses": vida_media_meses,
        "churn_rate": churn,
        "razao_ltv_cac": razao_ltv_cac,
        "ltv_cac_interpretacao": "Excelente (> 3:1)" if razao_ltv_cac > 3 else "Bom (2-3:1)" if razao_ltv_cac > 2 else "Precisa melhorar (< 2:1)",
        "churn_interpretacao": "Baixo (saudável)" if churn < 5 else "Moderado" if churn < 10 else "Alto (preocupante)",
    }


def calcular_metricas_escala(clientes_ini: int, clientes_meta: int, preco: float,
                               custo_fixo: float, custo_var_unit: float, meses_projecao: int = 12) -> list[dict]:
    projecoes = []
    clientes = clientes_ini
    crescimento_mensal = (clientes_meta / clientes_ini) ** (1 / meses_projecao) - 1

    for mes in range(1, meses_projecao + 1):
        clientes = int(clientes_ini * ((1 + crescimento_mensal) ** mes))
        receita = clientes * preco
        custo_var_total = clientes * custo_var_unit
        lucro = receita - custo_fixo - custo_var_total
        projecoes.append({
            "mes": mes,
            "clientes": clientes,
            "receita": round(receita, 2),
            "custo_fixo": round(custo_fixo, 2),
            "custo_variavel": round(custo_var_total, 2),
            "lucro": round(lucro, 2),
            "lucro_acumulado": round(sum(p["lucro"] for p in projecoes) + lucro, 2),
        })

    return projecoes


def executar_todos_calculos(resultado_analise: dict) -> dict:
    custos = resultado_analise.get("custos_infraestrutura", {})
    risco = resultado_analise.get("matriz_risco", {})

    infra_anual = custos.get("infraestrutura", {}).get("total_anual", 2000)
    custo_fixo_mensal = round(infra_anual / 12, 2)

    # Usa o preço extraído pelo LLM; fallback para 99.99 só se ausente
    params = resultado_analise.get("parametros_extraidos", {})
    resumo = resultado_analise.get("resumo_features", {})
    preco = (
        params.get("preco_estimado")
        or resumo.get("preco")
        or custos.get("projecao_financeira", {}).get("preco_por_restaurante_mes")
        or 99.99
    )
    preco = float(preco)

    # 1. Investment
    investimento = calcular_investimento_inicial(infra_anual, dev_horas=2000)

    # 2. Pricing
    precificacao = calcular_precificacao(preco, custo_fixo_mensal, custo_variavel_por_cliente=2.50)

    # 3. Break-even
    ponto_eq = calcular_ponto_equilibrio(custo_fixo_mensal, preco, 2.50)

    # 4. Payback
    payback = calcular_payback(investimento["total"], 5, preco, custo_fixo_mensal, 2.50)
    payback_50 = calcular_payback(investimento["total"], 50, preco, custo_fixo_mensal, 2.50)

    # 5. VPL/TIR (5 year projection)
    fluxos = []
    for ano in range(1, 6):
        clientes_ano = min(5 * (2 ** (ano - 1)), 200)
        receita = clientes_ano * preco * 12
        cv = clientes_ano * 2.50 * 12
        lucro = receita - infra_anual - cv
        fluxos.append(round(lucro, 2))
    vpl_tir = calcular_vpl_tir(investimento["total"], fluxos)

    # 6. Performance (year 1)
    receita_ano1 = 5 * preco * 12
    performance = calcular_performance(
        receita_ano1, infra_anual,
        custo_variavel_total=5 * 2.50 * 12,
        investimento=investimento["total"],
    )

    # 7. Customer metrics
    metricas = calcular_metricas_cliente(
        clientes_atuais=5, novos_clientes_mes=3,
        cancelados_mes=0, gasto_marketing_mensal=500,
        receita_media_mes=preco, vida_media_meses=24,
    )

    # 8. Scale projection
    projecao = calcular_metricas_escala(5, 50, preco, custo_fixo_mensal, 2.50, 12)

    score_risco = risco.get("score_global", {}).get("score_risco_global", 0)
    parecer = risco.get("score_global", {}).get("parecer", "")

    return {
        "investimento_inicial": investimento,
        "precificacao": precificacao,
        "ponto_equilibrio": ponto_eq,
        "payback": {"5_clientes": payback, "50_clientes": payback_50},
        "vpl_tir": vpl_tir,
        "performance": performance,
        "metricas_cliente": metricas,
        "projecao_12_meses": projecao,
        "resumo_executivo": {
            "score_risco": score_risco,
            "parecer_risco": parecer,
            "investimento_total": investimento["total"],
            "custo_mensal": custo_fixo_mensal,
            "preco": preco,
            "break_even_clientes": ponto_eq["clientes_necessarios"],
            "payback_meses": payback["meses"],
            "lucro_ano1": performance["lucro_liquido"],
            "margem_liquida": performance["margem_liquida"],
            "roi": performance["roi"],
            "ltv": metricas["ltv"],
            "cac": metricas["cac"],
            "churn": metricas["churn_rate"],
        },
    }
