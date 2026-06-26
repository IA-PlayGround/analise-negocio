import re
import time
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from config import SEARXNG_URL

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

TIMEOUT_SITE = 10
TIMEOUT_DEEP = 8
TIMEOUT_SEARCH = 12


def extrair_conteudo_site(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SITE)
        response.raise_for_status()
    except requests.RequestException as exc:
        return f"[Erro ao acessar {url}: {exc}]"
    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    texto = soup.get_text(separator="\n", strip=True)
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    return "\n".join(linhas)


def _buscar_searxng_json(instance_url: str, query: str, max_results: int) -> list[dict]:
    url = f"{instance_url.rstrip('/')}/search"
    params = {
        "q": query,
        "format": "json",
        "language": "pt",
        "categories": "general",
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "link": item.get("url", ""),
                })
            return results
    except Exception:
        pass
    return []


def _buscar_searxng_html(instance_url: str, query: str, max_results: int) -> list[dict]:
    url = f"{instance_url.rstrip('/')}/search"
    params = {"q": query, "language": "pt", "categories": "general"}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for article in soup.find_all("article", class_="result")[:max_results]:
                title_el = article.find(["h3", "h4"])
                link_el = article.find("a", href=True)
                snippet_el = article.find("p", class_="content")
                results.append({
                    "title": title_el.get_text(strip=True) if title_el else "",
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "link": link_el["href"] if link_el else "",
                })
            return results
    except Exception:
        pass
    return []


def buscar_dados_mercado_searxng(termo_busca: str, max_results: int = 15) -> dict:
    if not SEARXNG_URL:
        return {"organic": [], "fonte": "searxng", "instancia": None}

    results = _buscar_searxng_json(SEARXNG_URL, termo_busca, max_results)
    if results:
        return {"organic": results, "fonte": "searxng", "instancia": SEARXNG_URL}

    results = _buscar_searxng_html(SEARXNG_URL, termo_busca, max_results)
    if results:
        return {"organic": results, "fonte": "searxng", "instancia": SEARXNG_URL}

    return {"organic": [], "fonte": "searxng", "instancia": SEARXNG_URL}


def buscar_dados_mercado(termo_busca: str, max_results: int = 15) -> dict:
    resultado = buscar_dados_mercado_searxng(termo_busca, max_results)
    if resultado.get("organic"):
        return resultado

    results = []
    try:
        with DDGS(timeout=TIMEOUT_SEARCH) as ddgs:
            for r in ddgs.text(termo_busca, region="br-pt", max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "link": r.get("href", ""),
                })
    except Exception:
        pass

    if results:
        return {"organic": results, "fonte": "duckduckgo"}

    try:
        with DDGS(timeout=TIMEOUT_SEARCH) as ddgs:
            for r in ddgs.text(termo_busca, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "link": r.get("href", ""),
                })
    except Exception:
        pass

    return {"organic": results, "fonte": "duckduckgo"}


def buscar_precos_em_sites(resultados: dict, max_sites: int = 8) -> list[float]:
    urls = [
        item.get("link", "")
        for item in resultados.get("organic", [])
        if item.get("link", "").startswith("http")
    ]
    if not urls:
        return []

    todos_precos = []
    visitados = 0
    termos_preco_url = [
        "preco", "preço", "plano", "pricing", "planos", "precos",
        "valor", "mensal", "mensalidade", "assinatura", "plan",
        "price", "prices", "precios",
    ]

    for url in urls:
        if visitados >= max_sites:
            break
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_DEEP)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            trechos_relevantes = []

            for tag in soup.find_all(["section", "div", "article", "main", "table", "li", "span", "p"]):
                texto_tag = tag.get_text(strip=True).lower()
                if any(t in texto_tag for t in termos_preco_url):
                    trechos_relevantes.append(tag.get_text(separator=" ", strip=True))

            if not trechos_relevantes:
                for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
                    texto_tag = tag.get_text(strip=True).lower()
                    if any(t in texto_tag for t in termos_preco_url):
                        trechos_relevantes.append(tag.get_text(separator=" ", strip=True))

            if not trechos_relevantes:
                body = soup.find("body")
                if body:
                    trechos_relevantes.append(body.get_text(separator=" ", strip=True)[:3000])

            texto_final = " ".join(trechos_relevantes)
            precos = extract_prices_from_text(texto_final)
            todos_precos.extend(precos)
            visitados += 1

        except (requests.RequestException, Exception):
            continue

    seen = set()
    unicos = []
    for p in todos_precos:
        if p not in seen:
            seen.add(p)
            unicos.append(p)
    return sorted(unicos)


def extrair_snippets(resultados: dict) -> str:
    return " ".join(
        item.get("snippet", "") for item in resultados.get("organic", [])
    )


def extrair_precos_concorrentes(resultados: dict) -> list[float]:
    snippets = [
        item.get("snippet", "") for item in resultados.get("organic", [])
    ]
    titles = [
        item.get("title", "") for item in resultados.get("organic", [])
    ]
    all_text = " ".join(snippets + titles)
    return extract_prices_from_text(all_text)


def extract_prices_from_text(text: str) -> list[float]:
    # Padrões ordenados do mais específico (contexto de preço explícito) para o mais genérico.
    # O último padrão genérico foi removido para evitar falsos positivos (datas, IDs, etc.).
    patterns = [
        r"R\$\s*(\d{1,4}[.,]?\d*)",
        r"(\d{1,4}[.,]\d{2})\s*(?:reais|BRL)",
        r"(?:a partir de|por apenas|por|preço[:\s]+|custa[:\s]+)\s*R?\$?\s*(\d{1,4}[.,]?\d*)",
        r"(\d{1,4}[.,]?\d*)\s*(?:\/mês|\/mes|\/month|mensal|mensais)",
        r"(?:plano|plans|assinatura)\s*(?:a partir de\s*)?R?\$?\s*(\d{1,4}[.,]?\d*)",
    ]

    prices = []
    for pattern in patterns:
        for match in re.findall(pattern, text, re.IGNORECASE):
            try:
                value = float(match.replace(",", "."))
                if 3 < value < 5000:
                    prices.append(round(value, 2))
            except ValueError:
                continue
    return prices


def buscar_termos_precificacao(nicho: str, nome_produto: str = "") -> list[str]:
    queries = []
    base = nome_produto or nicho
    palavras = nicho.lower().replace(",", " ").split()
    nucleo = " ".join([w for w in palavras if len(w) > 3][:3])

    queries.append(f"{base} preço plano mensal")
    queries.append(f"{nucleo} software preço mensalidade")
    queries.append(f"sistema {nucleo} valor plano assinatura")
    queries.append(f"{nucleo} concorrentes preço comparativo")
    return queries


def buscar_precos_multiplas_consultas(nicho: str, nome_produto: str = "") -> list[float]:
    queries = buscar_termos_precificacao(nicho, nome_produto)
    todos_precos = []

    for q in queries:
        try:
            res = buscar_dados_mercado(q, max_results=5)
            precos_snippets = extrair_precos_concorrentes(res)
            precos_sites = buscar_precos_em_sites(res, max_sites=3)
            todos_precos.extend(precos_snippets)
            todos_precos.extend(precos_sites)
        except Exception:
            continue
        time.sleep(0.3)

    seen = set()
    unicos = []
    for p in todos_precos:
        if p not in seen:
            seen.add(p)
            unicos.append(p)
    return sorted(unicos)


def extrair_entidades_concorrentes(resultados: dict) -> list[str]:
    return [
        item.get("title", "") for item in resultados.get("organic", [])
    ]


def buscar_precos_concorrentes_conhecidos(nomes_concorrentes: list[str]) -> list[dict]:
    resultados = []
    for nome in nomes_concorrentes:
        query = f"{nome} preço plano mensalidade valor"
        try:
            res = buscar_dados_mercado(query, max_results=3)
            precos_snippets = extrair_precos_concorrentes(res)
            precos_sites = buscar_precos_em_sites(res, max_sites=1)
            todos = sorted(set(precos_snippets + precos_sites))
            resultados.append({
                "concorrente": nome,
                "precos_encontrados": todos,
            })
        except Exception:
            resultados.append({
                "concorrente": nome,
                "precos_encontrados": [],
            })
        time.sleep(0.3)
    return resultados


PAGINAS_TAXAS_CONCORRENTES = {
    "iFood": [
        "https://parceiros.ifood.com.br/restaurante",
    ],
    "99Food": [
        "https://merchant.99app.com/pt-BR/store",
    ],
    "Goomer": [
        "https://goomer.com.br/planos",
        "https://goomer.com.br/precos",
    ],
    "Anota AI": [
        "https://anota.ai/planos",
        "https://anota.ai/precos",
    ],
    "Saipos": [
        "https://saipos.com/planos",
        "https://saipos.com/precos",
    ],
    "Cardápio Web": [
        "https://cardapio.digital/planos",
        "https://www.cardapiodigital.com/precos",
    ],
}


def buscar_taxas_pagina_oficial(nomes_concorrentes: list[str]) -> list[dict]:
    resultados = []
    for nome in nomes_concorrentes:
        precos = []
        urls = PAGINAS_TAXAS_CONCORRENTES.get(nome, [])
        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_DEEP)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                texto = soup.get_text(separator=" ", strip=True)
                encontrados = extract_prices_from_text(texto)
                precos.extend(encontrados)
            except Exception:
                continue
            time.sleep(0.3)

        resultados.append({
            "concorrente": nome,
            "precos_encontrados": sorted(set(precos)),
        })
    return resultados


def extrair_precos_usd(text: str) -> list[float]:
    patterns = [
        r"\$\s*(\d{1,3}[.,]?\d*)\s*(?:\/mo|\/month|per\s*month|a\s*month|month)?",
        r"(\d{1,3}[.,]?\d*)\s*(?:USD|dollars?)\s*(?:\/mo|per\s*month)?",
        r"(?:starting|from|at)\s+\$\s*(\d{1,3}[.,]?\d*)",
    ]
    prices = []
    for pattern in patterns:
        for match in re.findall(pattern, text, re.IGNORECASE):
            try:
                value = float(match.replace(",", "."))
                if 1 < value < 500:
                    prices.append(round(value, 2))
            except ValueError:
                continue
    return prices


QUERIES_PROVEDORES = {
    "vps": [
        "Contabo Hetzner Hostinger VPS preço mensal reais comparativo 2025",
        "melhor VPS barato custo-benefício Brasil hospedagem",
    ],
    "docker": [
        "VPS Docker hospedagem preço mensal 2025 Hetzner Contabo",
        "servidor Linux Docker container barato preço",
    ],
    "swarm": [
        "Docker Swarm VPS múltiplos nós hospedagem preço mensal",
    ],
    "k8s": [
        "Kubernetes gerenciado preço 2025 DigitalOcean Hetzner K3s comparativo",
        "K8s managed cluster custo mensal Brasil dólares",
    ],
    "serverless": [
        "Vercel Netlify Cloudflare Workers preço plano 2025 comparativo",
        "serverless hosting gratuito pago preço mensal",
    ],
    "paas": [
        "Railway Render Fly.io Heroku preço plano mensal 2025",
        "PaaS hospedagem melhor preço custo-benefício comparativo",
    ],
    "bare": [
        "bare metal dedicado preço mensal OVH Hetzner Contabo 2025",
        "servidor dedicado hospedagem barata reais",
    ],
}

FAIXAS_PRECO_INFRA_BRL = {
    "vps": (15, 600),
    "docker": (20, 700),
    "swarm": (80, 2000),
    "k8s": (80, 3000),
    "serverless": (5, 500),
    "paas": (5, 400),
    "bare": (200, 4000),
}


def buscar_precos_provedores_infra(tipo_infra: str) -> list[float]:
    """Search the web for current provider prices for the given infra type. Returns BRL prices found."""
    queries = QUERIES_PROVEDORES.get(tipo_infra, QUERIES_PROVEDORES["vps"])
    lo, hi = FAIXAS_PRECO_INFRA_BRL.get(tipo_infra, (15, 600))
    todos = []

    for q in queries:
        try:
            res = buscar_dados_mercado(q, max_results=5)
            texto = " ".join(
                item.get("snippet", "") + " " + item.get("title", "")
                for item in res.get("organic", [])
            )
            precos_brl = extract_prices_from_text(texto)
            precos_usd = extrair_precos_usd(texto)
            precos_brl += [round(p * 5.5, 2) for p in precos_usd]
            todos.extend(precos_brl)
        except Exception:
            continue
        time.sleep(0.3)

    return sorted({p for p in todos if lo <= p <= hi})
