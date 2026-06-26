#!/usr/bin/env python3
import json
import sys
from config import validate_config
from llm_extractor import extrair_parametros_ia, resumir_features_site, analisar_semantica_projeto
from web_search import (
    extrair_conteudo_site,
    buscar_dados_mercado,
    buscar_precos_multiplas_consultas,
    buscar_precos_concorrentes_conhecidos,
    buscar_taxas_pagina_oficial,
    buscar_precos_provedores_infra,
    extrair_snippets,
    extrair_precos_concorrentes,
    extrair_entidades_concorrentes,
)
from risk_engine import (
    calcular_risco_concorrencia,
    calcular_risco_preco,
    calcular_hhi,
    calcular_risco_global,
)
from project_analyzer import (
    analisar_diretorio_projeto,
    calcular_custos_infra,
    INFRA_TIPOS,
)
from financial_engine import executar_todos_calculos
from report_generator import gerar_relatorio_html


INFRA_OPCOES = {
    "1": "vps",
    "2": "docker",
    "3": "swarm",
    "4": "k8s",
    "5": "serverless",
    "6": "paas",
    "7": "bare",
}


def solicitar_parametros_projeto() -> tuple[list[str], str, int, int]:
    """Prompts interativos para o modo de análise de diretório."""
    print("\n" + "─" * 60)
    print("  CONFIGURAÇÃO DA ANÁLISE")
    print("─" * 60)

    print("\n[CONCORRENTES]")
    print("  Liste os concorrentes do projeto separados por vírgula.")
    print("  Exemplo: Stripe, PagSeguro, Asaas, Mercado Pago")
    print("  Pressione ENTER para busca automática por concorrentes.")
    entrada = input("  Concorrentes: ").strip()
    concorrentes = [c.strip() for c in entrada.split(",") if c.strip()] if entrada else []

    print("\n[INFRAESTRUTURA]")
    for k, tipo in INFRA_OPCOES.items():
        print(f"  {k}. {INFRA_TIPOS.get(tipo, tipo)}")
    escolha = input("\n  Tipo de infraestrutura [1-7, padrão=1]: ").strip() or "1"
    tipo_infra = INFRA_OPCOES.get(escolha, "vps")
    print(f"  → {INFRA_TIPOS.get(tipo_infra, tipo_infra)}")

    print("\n[ESCALA]")
    ini = input("  Número inicial de clientes/usuários [padrão=5]: ").strip() or "5"
    meta = input("  Meta de clientes em 12 meses [padrão=50]: ").strip() or "50"
    try:
        clientes_ini = max(1, int(ini))
        clientes_meta = max(clientes_ini + 1, int(meta))
    except ValueError:
        clientes_ini, clientes_meta = 5, 50

    return concorrentes, tipo_infra, clientes_ini, clientes_meta


def executar_validacao_por_url(url: str, concorrentes_conhecidos: list[str] | None = None) -> dict:
    print("=" * 60)
    print("  SISTEMA DE VALIDAÇÃO MATEMÁTICA DE IDEIAS DE NEGÓCIO")
    print("=" * 60)

    print(f"\n[1/5] Extraindo conteúdo do site: {url}")
    conteudo_site = extrair_conteudo_site(url)
    print(f"  Conteúdo extraído: {len(conteudo_site)} caracteres")

    print("\n[2/5] IA analisando features do site...")
    resumo = resumir_features_site(conteudo_site)
    print(f"  Produto: {resumo.get('nome_produto', 'N/A')}")
    print(f"  Nicho: {resumo.get('nicho', 'N/A')}")
    print(f"  Preço: R$ {resumo.get('preco', 0)}")
    print(f"  Features: {len(resumo.get('features_principais', []))} identificadas")
    print(f"  Diferenciais: {len(resumo.get('diferenciais', []))} identificados")

    termo_busca = f"{resumo.get('nome_produto', '')} {resumo.get('nicho', '')} concorrentes"
    print(f"\n[3/5] Buscando concorrentes (SearXNG → DuckDuckGo): '{termo_busca.strip()}'...")
    resultados = buscar_dados_mercado(termo_busca.strip())
    snippets = extrair_snippets(resultados)
    entidades = extrair_entidades_concorrentes(resultados)
    precos_snippets = extrair_precos_concorrentes(resultados)

    fonte = resultados.get("fonte", "desconhecida")
    instancia = resultados.get("instancia", "")
    info_fonte = f"{fonte}" + (f" ({instancia})" if instancia else "")
    print(f"  Resultados encontrados: {len(resultados.get('organic', []))} via {info_fonte}")
    print(f"  Preços nos snippets: {precos_snippets if precos_snippets else 'Nenhum'}")

    print("\n[3.5/5] Buscas específicas por preços de concorrentes...")
    nicho = resumo.get("nicho", "")
    nome = resumo.get("nome_produto", "")
    precos_especificos = buscar_precos_multiplas_consultas(nicho, nome)
    todos_precos = sorted(set(precos_snippets + precos_especificos))

    if concorrentes_conhecidos:
        print("\n[3.6/5] Buscando preços de concorrentes específicos...")
        precos_busca = buscar_precos_concorrentes_conhecidos(concorrentes_conhecidos)
        for item in precos_busca:
            print(f"  {item['concorrente']} (busca): {item['precos_encontrados'] if item['precos_encontrados'] else 'não encontrado'}")
            todos_precos.extend(item["precos_encontrados"])

        print("\n[3.7/5] Extraindo taxas das páginas oficiais...")
        taxas_oficiais = buscar_taxas_pagina_oficial(concorrentes_conhecidos)
        for item in taxas_oficiais:
            print(f"  {item['concorrente']} (oficial): {item['precos_encontrados'] if item['precos_encontrados'] else 'não encontrado'}")
            todos_precos.extend(item["precos_encontrados"])
        todos_precos = sorted(set(todos_precos))

    print(f"  Preços consolidados: {todos_precos if todos_precos else 'Nenhum (SaaS frequentemente não publica preços)'}")

    preco_proposto = resumo.get("preco", 0) or 99.99

    print("\n[4/5] Calculando riscos matemáticos...")
    risco_conc = calcular_risco_concorrencia(snippets, nicho)
    resultado_preco = calcular_risco_preco(preco_proposto, todos_precos)
    resultado_hhi = calcular_hhi(entidades)

    print(f"  Risco de Concorrência: {risco_conc}/10")
    print(f"  Risco de Preço: {resultado_preco['risco_preco']}/10 — {resultado_preco['classificacao']}")
    if resultado_hhi.get("hhi") is not None:
        print(f"  HHI: {resultado_hhi['hhi']} — {resultado_hhi['classificacao']}")

    print("\n[5/5] Gerando score global final...")
    score_global = calcular_risco_global(
        risco_conc,
        resultado_preco["risco_preco"],
        resultado_hhi,
        todos_precos,
        preco_proposto,
    )

    relatorio = {
        "url_analisada": url,
        "resumo_features": resumo,
        "dados_mercado": {
            "num_resultados_busca": len(resultados.get("organic", [])),
            "precos_concorrentes_total": todos_precos,
            "estatistica_precos": {
                "media": resultado_preco.get("media_mercado"),
                "desvio_padrao": resultado_preco.get("desvio_padrao"),
                "z_score_proposto": resultado_preco.get("z_score"),
            },
        },
        "matriz_risco": {
            "risco_concorrencia": risco_conc,
            "risco_preco": resultado_preco,
            "indice_hhi": resultado_hhi,
            "score_global": score_global,
        },
    }

    print("\n" + "=" * 60)
    print("  RELATÓRIO DE VALIDAÇÃO")
    print("=" * 60)
    print(f"\n  Produto: {resumo.get('nome_produto', 'N/A')}")
    print(f"  Nicho: {nicho}")
    print(f"  Preço proposto: R$ {preco_proposto}")
    print(f"  Preços concorrentes: {todos_precos if todos_precos else 'Não detectados'}")
    if resultado_preco.get("media_mercado"):
        print(f"  Média de mercado: R$ {resultado_preco['media_mercado']}")
        print(f"  Desvio padrão: R$ {resultado_preco['desvio_padrao']}")
        print(f"  Z-Score do preço: {resultado_preco['z_score']}")
    print(f"  Score de Risco Global: {score_global['score_risco_global']}/10")
    print(f"  Parecer: {score_global['parecer']}")
    print("=" * 60)

    return relatorio


def executar_validacao_texto(ideia_negocio: str) -> dict:
    print("=" * 60)
    print("  SISTEMA DE VALIDAÇÃO MATEMÁTICA DE IDEIAS DE NEGÓCIO")
    print("=" * 60)

    print("\n[1/4] IA analisando a ideia...")
    parametros = extrair_parametros_ia(ideia_negocio)
    print(f"  Nicho identificado: {parametros.get('nicho', 'N/A')}")
    print(f"  Preço estimado: R$ {parametros.get('preco_estimado', 'N/A')}")
    print(f"  Região: {parametros.get('regiao', 'N/A')}")

    print(f"\n[2/4] Buscando dados de mercado (SearXNG → DuckDuckGo): '{parametros['termo_busca']}'...")
    resultados = buscar_dados_mercado(parametros["termo_busca"])
    snippets = extrair_snippets(resultados)
    entidades = extrair_entidades_concorrentes(resultados)
    precos_snippets = extrair_precos_concorrentes(resultados)

    fonte = resultados.get("fonte", "desconhecida")
    instancia = resultados.get("instancia", "")
    info_fonte = f"{fonte}" + (f" ({instancia})" if instancia else "")
    print(f"  Resultados encontrados: {len(resultados.get('organic', []))} via {info_fonte}")
    print(f"  Preços nos snippets: {precos_snippets if precos_snippets else 'Nenhum'}")

    print("\n[2.5/4] Buscas específicas por preços de concorrentes...")
    nicho = parametros.get("nicho", "")
    precos_especificos = buscar_precos_multiplas_consultas(nicho)
    todos_precos = sorted(set(precos_snippets + precos_especificos))
    print(f"  Preços encontrados: {todos_precos if todos_precos else 'Nenhum'}")

    print("\n[3/4] Calculando riscos matemáticos...")
    risco_conc = calcular_risco_concorrencia(snippets, nicho)
    resultado_preco = calcular_risco_preco(
        parametros["preco_estimado"], todos_precos
    )
    resultado_hhi = calcular_hhi(entidades)

    print(f"  Risco de Concorrência: {risco_conc}/10")
    print(f"  Risco de Preço: {resultado_preco['risco_preco']}/10 — {resultado_preco['classificacao']}")
    if resultado_hhi.get("hhi") is not None:
        print(f"  HHI: {resultado_hhi['hhi']} — {resultado_hhi['classificacao']}")

    print("\n[4/4] Gerando score global final...")
    score_global = calcular_risco_global(
        risco_conc,
        resultado_preco["risco_preco"],
        resultado_hhi,
        todos_precos,
        parametros["preco_estimado"],
    )

    relatorio = {
        "ideia_analisada": ideia_negocio.strip(),
        "parametros_extraidos": parametros,
        "dados_mercado": {
            "num_resultados_busca": len(resultados.get("organic", [])),
            "precos_concorrentes_total": todos_precos,
            "estatistica_precos": {
                "media": resultado_preco.get("media_mercado"),
                "desvio_padrao": resultado_preco.get("desvio_padrao"),
                "z_score_proposto": resultado_preco.get("z_score"),
            },
        },
        "matriz_risco": {
            "risco_concorrencia": risco_conc,
            "risco_preco": resultado_preco,
            "indice_hhi": resultado_hhi,
            "score_global": score_global,
        },
    }

    print("\n" + "=" * 60)
    print("  RELATÓRIO DE VALIDAÇÃO")
    print("=" * 60)
    print(f"\n  Score de Risco Global: {score_global['score_risco_global']}/10")
    print(f"  Parecer: {score_global['parecer']}")
    print("=" * 60)

    return relatorio


def executar_validacao_projeto(
    caminho_dir: str,
    concorrentes: list[str] | None = None,
    tipo_infra: str = "vps",
    clientes_ini: int = 5,
    clientes_meta: int = 50,
) -> dict:
    print("=" * 60)
    print("  SISTEMA DE VALIDAÇÃO MATEMÁTICA DE IDEIAS DE NEGÓCIO")
    print("  MODO: ANÁLISE DE PROJETO")
    print("=" * 60)

    print(f"\n[1/7] Analisando diretório: {caminho_dir}")
    analise = analisar_diretorio_projeto(caminho_dir)
    linguagens_str = ", ".join(analise["linguagens"].keys()) or "N/A"
    frameworks_str = ", ".join(analise["frameworks"][:5]) or "N/A"
    print(f"  Projeto: {analise['nome']}")
    print(f"  Arquivos: {analise['total_arquivos']} · Linhas: {analise['total_linhas']:,}")
    print(f"  Linguagens: {linguagens_str}")
    print(f"  Frameworks: {frameworks_str}")
    print(f"  Bancos: {', '.join(analise['bancos']) or 'N/A'}")
    print(f"  Infra detectada: {', '.join(analise['infra']) or 'N/A'}")
    servicos_list = analise["servicos_externos"][:8]
    print(f"  Serviços externos: {', '.join(servicos_list) if servicos_list else 'N/A'}")

    print(f"\n[2/7] IA analisando semântica do projeto...")
    semantica = analisar_semantica_projeto(analise)
    print(f"  Tipo: {semantica.get('tipo_produto', 'N/A')}")
    print(f"  Nicho: {semantica.get('nicho', 'N/A')}")
    print(f"  Descrição: {semantica.get('descricao', 'N/A')[:120]}...")
    print(f"  Modelo de negócio: {semantica.get('modelo_negocio', 'N/A')}")
    print(f"  Preço estimado: R$ {semantica.get('preco_estimado', 'N/A')}")

    termo_busca = semantica.get("termo_busca") or f"{semantica.get('nicho', '')} software concorrentes"
    nicho = semantica.get("nicho", "")
    preco_proposto = semantica.get("preco_estimado") or 99.99

    print(f"\n[3/7] Buscando concorrentes (SearXNG → DuckDuckGo): '{termo_busca}'...")
    resultados = buscar_dados_mercado(termo_busca)
    snippets = extrair_snippets(resultados)
    entidades = extrair_entidades_concorrentes(resultados)
    precos_snippets = extrair_precos_concorrentes(resultados)
    fonte = resultados.get("fonte", "desconhecida")
    print(f"  Resultados: {len(resultados.get('organic', []))} via {fonte}")

    print("\n[4/7] Buscas específicas de preços de concorrentes...")
    precos_especificos = buscar_precos_multiplas_consultas(nicho)
    todos_precos = sorted(set(precos_snippets + precos_especificos))

    if concorrentes:
        print(f"  Buscando {len(concorrentes)} concorrente(s) informado(s)...")
        precos_busca = buscar_precos_concorrentes_conhecidos(concorrentes)
        taxas_oficiais = buscar_taxas_pagina_oficial(concorrentes)
        for item in precos_busca:
            todos_precos.extend(item["precos_encontrados"])
            print(f"  {item['concorrente']}: {item['precos_encontrados'] or 'sem preço público'}")
        for item in taxas_oficiais:
            todos_precos.extend(item["precos_encontrados"])
        todos_precos = sorted(set(todos_precos))

    print(f"  Preços consolidados: {todos_precos or 'Nenhum detectado (SaaS frequentemente não publica)'}")

    print("\n[5/7] Calculando riscos matemáticos...")
    risco_conc = calcular_risco_concorrencia(snippets, nicho)
    resultado_preco = calcular_risco_preco(preco_proposto, todos_precos)
    resultado_hhi = calcular_hhi(entidades)
    score_global = calcular_risco_global(
        risco_conc, resultado_preco["risco_preco"], resultado_hhi,
        todos_precos, preco_proposto,
    )
    print(f"  Risco de Concorrência: {risco_conc}/10")
    print(f"  Risco de Preço: {resultado_preco['risco_preco']}/10 — {resultado_preco['classificacao']}")
    print(f"  Score Global: {score_global['score_risco_global']}/10 — {score_global['parecer']}")

    print(f"\n[6/7] Pesquisando provedores de infraestrutura ({INFRA_TIPOS.get(tipo_infra, tipo_infra)})...")
    precos_web = buscar_precos_provedores_infra(tipo_infra)
    if precos_web:
        print(f"  Preços encontrados na web: R${min(precos_web):.0f} – R${max(precos_web):.0f}")
    else:
        print("  Usando preços de referência (dados web indisponíveis)")

    custos = calcular_custos_infra(
        analise["estimativa_recursos"],
        tipo_infra=tipo_infra,
        clientes_ini=clientes_ini,
        clientes_meta=clientes_meta,
        precos_web=precos_web,
    )

    top = custos["infraestrutura"]["provedores_top"]
    print(f"\n  TOP PROVEDORES para {INFRA_TIPOS.get(tipo_infra, tipo_infra)}:")
    for i, p in enumerate(top[:5], 1):
        ram_label = f"{p['ram_gb']}GB RAM" if p.get("ram_gb") else "RAM flexível"
        vcpu_label = f"{p['vcpu']} vCPU" if p.get("vcpu") else ""
        specs = ", ".join(filter(None, [vcpu_label, ram_label]))
        nota = f"  ← {p['nota']}" if p.get("nota") else ""
        print(f"  {i}. {p['nome']:35s} R${p['preco_mes_brl']:>6.0f}/mês  ({specs}){nota}")

    print(f"\n  Recomendado: {custos['infraestrutura']['recomendado']}")
    print(f"  Custo mensal: R$ {custos['infraestrutura']['custo_mensal']}/mês")
    print(f"  Serviços ext.: R$ {custos['infraestrutura']['servicos_externos']['custo_mensal']}/mês")
    print(f"  Total anual: R$ {custos['infraestrutura']['total_anual']}")

    relatorio = {
        "analise_projeto": analise,
        "analise_semantica": semantica,
        "parametros_extraidos": {
            "nicho": nicho,
            "preco_estimado": preco_proposto,
            "termo_busca": termo_busca,
        },
        "dados_mercado": {
            "precos_concorrentes_total": todos_precos,
            "estatistica_precos": {
                "media": resultado_preco.get("media_mercado"),
                "desvio_padrao": resultado_preco.get("desvio_padrao"),
                "z_score_proposto": resultado_preco.get("z_score"),
            },
        },
        "matriz_risco": {
            "risco_concorrencia": risco_conc,
            "risco_preco": resultado_preco,
            "indice_hhi": resultado_hhi,
            "score_global": score_global,
        },
        "custos_infraestrutura": custos,
    }

    print("\n" + "=" * 60)
    print(f"  PROJETO: {analise['nome']}")
    print(f"  {analise['total_arquivos']} arquivos · {analise['total_linhas']:,} linhas")
    print(f"  {semantica.get('tipo_produto', '')} · {nicho}")
    print(f"\n  INFRA ({INFRA_TIPOS.get(tipo_infra, tipo_infra)}):")
    print(f"    Recomendado: {custos['infraestrutura']['recomendado']}")
    print(f"    Custo inicial: R$ {custos['infraestrutura']['custo_mensal']}/mês")
    print(f"    Total 1 ano: R$ {custos['infraestrutura']['total_anual']}")
    print(f"\n  ESCALA ({clientes_ini} → {clientes_meta} clientes em 12 meses):")
    print(f"    Custo/cliente: R$ {custos['escala']['custo_por_cliente_mes']}/mês")
    req = custos["escala"]["requisicoes"]
    print(f"    {clientes_ini} clientes → {req['dia_inicial']:,} req/dia")
    print(f"    {clientes_meta} clientes → {req['dia_meta']:,} req/dia")
    print(f"\n  RISCO: {score_global['score_risco_global']}/10 — {score_global['parecer']}")
    print("=" * 60)

    print("\n[7/7] Calculando métricas financeiras completas...")
    calculos = executar_todos_calculos(relatorio)
    relatorio["calculos_financeiros"] = calculos
    res = calculos["resumo_executivo"]
    print(f"  Investimento inicial: R$ {res['investimento_total']:,.0f}")
    print(f"  Break-even: {res['break_even_clientes']} clientes")
    print(f"  Payback: {res['payback_meses']} meses")
    print(f"  Lucro Ano 1: R$ {res['lucro_ano1']:,.2f} ({res['margem_liquida']}%)")
    print(f"  LTV: R$ {res['ltv']:,.2f} | CAC: R$ {res['cac']:,.2f} | Churn: {res['churn']}%")

    print("\n[HTML] Gerando relatório financeiro profissional...")
    html_path = gerar_relatorio_html(relatorio)
    print(f"  ✅ {html_path}")

    return relatorio


def main():
    validate_config()

    concorrentes = None
    dir_projeto = None
    tipo_infra = None
    clientes_ini = None
    clientes_meta = None
    remaining = []
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a in ("--concorrentes", "-c") and i + 1 < len(sys.argv):
            concorrentes = [c.strip() for c in sys.argv[i + 1].split(",")]
            i += 2
        elif a in ("--dir", "-d") and i + 1 < len(sys.argv):
            dir_projeto = sys.argv[i + 1]
            i += 2
        elif a == "--infra" and i + 1 < len(sys.argv):
            tipo_infra = sys.argv[i + 1].lower()
            i += 2
        elif a == "--escala" and i + 1 < len(sys.argv):
            partes = sys.argv[i + 1].split(":")
            try:
                clientes_ini = int(partes[0])
                clientes_meta = int(partes[1]) if len(partes) > 1 else clientes_ini * 10
            except (ValueError, IndexError):
                pass
            i += 2
        else:
            remaining.append(a)
            i += 1

    if dir_projeto:
        # Interactive prompts only for parameters not passed via CLI
        if concorrentes is None or tipo_infra is None:
            c_input, t_input, ini_input, meta_input = solicitar_parametros_projeto()
            if concorrentes is None:
                concorrentes = c_input
            if tipo_infra is None:
                tipo_infra = t_input
            if clientes_ini is None:
                clientes_ini = ini_input
            if clientes_meta is None:
                clientes_meta = meta_input
        print()
        resultado = executar_validacao_projeto(
            dir_projeto,
            concorrentes=concorrentes or None,
            tipo_infra=tipo_infra or "vps",
            clientes_ini=clientes_ini or 5,
            clientes_meta=clientes_meta or 50,
        )
    elif remaining:
        arg = remaining[0]
        if arg.startswith("http://") or arg.startswith("https://"):
            print(f"Modo: Análise de site ({arg})")
            if concorrentes:
                print(f"Concorrentes conhecidos: {', '.join(concorrentes)}")
            print()
            resultado = executar_validacao_por_url(arg, concorrentes)
        else:
            with open(arg, "r") as f:
                ideia_negocio = f.read()
            if ideia_negocio.strip().startswith("http"):
                url = ideia_negocio.strip().split("\n")[0]
                print(f"Modo: Análise de site ({url})\n")
                resultado = executar_validacao_por_url(url, concorrentes)
            else:
                print("Modo: Análise de ideia (arquivo de texto)\n")
                resultado = executar_validacao_texto(ideia_negocio)
    else:
        ideia_padrao = """
Quero criar uma cafeteria drive-thru automatizada voltada para cafés gourmet
rápidos em áreas corporativas de São Paulo, cobrando um preço médio de R$ 15 por café.
"""
        print("Usando ideia de exemplo.\n")
        print("Uso:")
        print("  python main.py --dir <diretório> [--infra vps|docker|k8s|paas|serverless|swarm|bare]")
        print("                                   [--concorrentes nome1,nome2] [--escala ini:meta]")
        print("  python main.py <url> [--concorrentes nome1,nome2]")
        print("  python main.py <arquivo.txt>\n")
        resultado = executar_validacao_texto(ideia_padrao)

    with open("relatorio_validacao.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print("\nRelatório salvo em: relatorio_validacao.json")


if __name__ == "__main__":
    main()
