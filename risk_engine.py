import numpy as np
from scipy import stats

TERMOS_GENERICOS = [
    "concorrente", "mercado", "franquia", "rede", "expansão",
    "concorrência", "saturado", "crescimento", "player",
    "startup", "plataforma", "lider", "dominante",
    "disputa", "rival", "consolidado", "aquisição",
    "rodada", "investimento", "valuation", "market share",
]


def gerar_termos_nicho(nicho: str) -> list[str]:
    return [p.strip().lower() for p in nicho.lower().replace(",", " ").split() if len(p.strip()) > 2]


def calcular_risco_concorrencia(snippets_concatenados: str, nicho: str = "") -> float:
    texto = snippets_concatenados.lower()
    termos = list(TERMOS_GENERICOS)

    if nicho:
        termos.extend(gerar_termos_nicho(nicho))

    contagem = sum(texto.count(t) for t in termos)
    risco = min(10, contagem * 0.6)
    return round(risco, 2)


def calcular_risco_preco(preco_proposto: float, precos_concorrentes: list[float]) -> dict:
    if not precos_concorrentes:
        return {
            "risco_preco": 5.0,
            "media_mercado": None,
            "desvio_padrao": None,
            "classificacao": "Indeterminado (sem dados de concorrentes)",
        }

    precos = np.array(precos_concorrentes)
    media = float(np.mean(precos))
    desvio = float(np.std(precos, ddof=1)) if len(precos) > 1 else 0.0
    z_score = abs(preco_proposto - media) / desvio if desvio > 0 else 0.0

    if z_score > 2.0:
        risco = min(10, z_score * 2.5)
        classificacao = "Altíssimo (preço > 2 desvios padrão da média)"
    elif z_score > 1.5:
        risco = min(10, z_score * 2.0)
        classificacao = "Alto (preço entre 1.5 e 2 desvios padrão)"
    elif z_score > 1.0:
        risco = z_score * 2.5
        classificacao = "Moderado (preço entre 1 e 1.5 desvios padrão)"
    elif z_score > 0.5:
        risco = z_score * 2.0
        classificacao = "Baixo (preço dentro de 1 desvio padrão)"
    else:
        risco = z_score * 1.5
        classificacao = "Muito Baixo (preço próximo da média de mercado)"

    return {
        "risco_preco": round(risco, 2),
        "media_mercado": round(media, 2),
        "desvio_padrao": round(desvio, 2),
        "z_score": round(z_score, 2),
        "classificacao": classificacao,
    }


def calcular_hhi(entidades_concorrentes: list[str]) -> dict:
    if not entidades_concorrentes:
        return {
            "hhi": None,
            "classificacao": "Indeterminado (sem dados)",
            "num_players": 0,
        }

    n = len(entidades_concorrentes)
    if n == 1:
        shares = np.array([100.0])
    else:
        base_share = 100 / n
        shares = np.full(n, base_share)

        keyword_multipliers = [
            1.5 if any(k in e.lower() for k in ["grande", "rede", "lider"])
            else 0.5 if any(k in e.lower() for k in ["pequeno", "local"])
            else 1.0
            for e in entidades_concorrentes
        ]
        weighted = shares * np.array(keyword_multipliers)
        shares = (weighted / weighted.sum()) * 100

    hhi = float(np.sum(np.square(shares)))

    if hhi > 2500:
        classificacao = "Altamente Concentrado (risco elevado para novos entrantes)"
    elif hhi > 1500:
        classificacao = "Moderadamente Concentrado (risco moderado)"
    elif hhi > 1000:
        classificacao = "Pouco Concentrado (mercado competitivo, risco baixo)"
    else:
        classificacao = "Desconcentrado (mercado fragmentado, oportunidade)"

    return {
        "hhi": round(hhi, 2),
        "classificacao": classificacao,
        "num_players": n,
    }


def calcular_risco_global(
    risco_concorrencia: float,
    risco_preco: float,
    hhi_result: dict,
    precos_concorrentes: list[float],
    preco_proposto: float,
) -> dict:
    fator_hhi = 0.0
    if hhi_result.get("hhi") is not None:
        fator_hhi = min(10, hhi_result["hhi"] / 1000)

    score = (
        risco_concorrencia * 0.30
        + risco_preco * 0.30
        + fator_hhi * 0.25
    )

    if precos_concorrentes:
        volatility = float(np.std(precos_concorrentes)) if len(precos_concorrentes) > 1 else 0.0
        score += min(2.5, volatility * 0.5) * 0.15
    else:
        volatility = 0
        score += 0.375

    score = round(min(10, score), 2)

    if score >= 7:
        parecer = "ALTO RISCO: Desaconselhável prosseguir sem diferenciação clara."
    elif score >= 4:
        parecer = "RISCO MODERADO: Viável com estratégia de diferenciação e preço competitivo."
    elif score >= 2:
        parecer = "RISCO BAIXO: Mercado favorável, oportunidade identificada."
    else:
        parecer = "RISCO MUITO BAIXO: Condições de mercado ideais para entrada."

    return {
        "score_risco_global": score,
        "parecer": parecer,
        "pesos": {
            "concorrencia": "30%",
            "preco": "30%",
            "concentracao_mercado_hhi": "25%",
            "volatilidade_precos": "15%",
            "volatilidade_detectada": round(volatility, 2),
        },
    }
