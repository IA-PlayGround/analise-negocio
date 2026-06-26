import json
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_URL


def consultar_llm(prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }

    response = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def extrair_parametros_ia(texto_ideia: str) -> dict:
    prompt = f"""
Com base na seguinte ideia de negócio, extraia as informações no formato JSON estrito.
Retorne APENAS o JSON, sem texto adicional.

Ideia: {texto_ideia}

Campos do JSON:
- "termo_busca": (string otimizada para buscar concorrentes no Google, em português)
- "preco_estimado": (número float, preço médio estimado do produto/serviço extraído ou sugerido)
- "nicho": (string curta do setor de mercado)
- "regiao": (string da região geográfica alvo, se mencionada)
- "palavras_chave_secundarias": (lista de 2 a 4 strings com termos complementares de busca)
"""
    return consultar_llm(prompt)


def analisar_semantica_projeto(analise_tecnica: dict) -> dict:
    linguagens = ", ".join(analise_tecnica.get("linguagens", {}).keys()) or "N/A"
    frameworks = ", ".join(analise_tecnica.get("frameworks", [])[:8]) or "N/A"
    bancos = ", ".join(analise_tecnica.get("bancos", [])) or "Nenhum"
    servicos = ", ".join(analise_tecnica.get("servicos_externos", [])[:8]) or "Nenhum"
    infra = ", ".join(analise_tecnica.get("infra", [])) or "Nenhum"
    nome = analise_tecnica.get("nome", "projeto")
    arquivos = analise_tecnica.get("total_arquivos", 0)
    linhas = analise_tecnica.get("total_linhas", 0)

    prompt = f"""
Analise as informações técnicas de um projeto de software e deduza o que ele faz.
Retorne APENAS um JSON estrito, sem texto adicional.

Projeto: {nome}
Linguagens: {linguagens}
Frameworks: {frameworks}
Bancos de dados: {bancos}
Serviços externos: {servicos}
Infraestrutura detectada: {infra}
Tamanho: {arquivos} arquivos · {linhas:,} linhas de código

Campos do JSON:
- "descricao": (string, 2-3 frases descrevendo o que o projeto provavelmente faz)
- "tipo_produto": (string: "SaaS B2B" | "SaaS B2C" | "API/Microserviço" | "E-commerce" | "Marketplace" | "App Mobile Backend" | "Ferramenta Interna" | "Outro")
- "nicho": (string curta do setor de mercado, ex: "gestão de restaurantes", "fintech", "e-commerce")
- "publico_alvo": (string descrevendo o público-alvo)
- "modelo_negocio": (string: "assinatura mensal" | "por uso" | "freemium" | "licença única" | "marketplace comissão")
- "preco_estimado": (número float, preço mensal estimado em BRL com base no nicho e complexidade)
- "termo_busca": (string otimizada para buscar concorrentes no Google, em português)
"""
    return consultar_llm(prompt)


def resumir_features_site(conteudo_site: str) -> dict:
    prompt = f"""
Analise o conteúdo abaixo extraído de um site de produto SaaS e extraia um resumo
das features no formato JSON estrito. Retorne APENAS o JSON.

Conteúdo do site:
{conteudo_site[:6000]}

Campos do JSON:
- "nome_produto": (string, nome do produto/serviço)
- "features_principais": (lista de strings com as 5 a 8 principais funcionalidades)
- "preco": (número float, preço mensal se disponível, ou 0 se não encontrado)
- "nicho": (string curta do setor de mercado)
- "publico_alvo": (string descrevendo o público-alvo)
- "diferenciais": (lista de strings com 3 a 5 diferenciais competitivos)
- "concorrentes_diretos_citados": (lista de strings com nomes de concorrentes se mencionados)
"""
    return consultar_llm(prompt)
