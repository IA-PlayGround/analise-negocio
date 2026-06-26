# Análise de Negócio por MVP

Plataforma de validação matemática de ideias e projetos de software antes de escalar. A partir de uma URL, um texto descritivo ou um diretório de projeto existente, o sistema pesquisa concorrentes em tempo real, calcula riscos de mercado (HHI, Z-Score, concorrência) e produz um relatório financeiro completo com VPL, TIR, break-even, payback, LTV/CAC e projeção de escala — com custo de infraestrutura calculado dinamicamente por tipo de provedor (VPS, Docker, Kubernetes, PaaS, Serverless e Bare Metal).

> **Valide o mercado antes de investir.** Identifique riscos, estime custos reais de infra e projete o retorno financeiro do seu MVP com dados reais coletados da web.

---

## Como funciona

```
Entrada (URL / texto / diretório)
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │  [1] ANÁLISE DE ENTRADA                             │
  │      • URL → extrai conteúdo HTML via BeautifulSoup │
  │      • Texto → extrai ideia diretamente             │
  │      • Diretório → detecta stack, conta linhas,     │
  │        frameworks, DBs, serviços externos           │
  └──────────────┬──────────────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────────────┐
  │  [2] ANÁLISE SEMÂNTICA via LLM (DeepSeek)           │
  │      • O que o projeto faz                          │
  │      • Tipo: SaaS B2B, API, E-commerce, etc.        │
  │      • Nicho, público-alvo, modelo de negócio       │
  │      • Preço estimado, termo de busca para concorr. │
  └──────────────┬──────────────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────────────┐
  │  [3] PESQUISA DE MERCADO (SearXNG → DuckDuckGo)     │
  │      • Busca concorrentes por nicho                 │
  │      • Extrai preços de snippets e páginas          │
  │      • Pesquisa concorrentes informados pelo usuário│
  │      • Acessa páginas oficiais de preços            │
  └──────────────┬──────────────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────────────┐
  │  [4] MATRIZ DE RISCO                                │
  │      • Risco de concorrência (frequência de termos) │
  │      • Risco de preço (Z-Score vs. mercado)         │
  │      • HHI — Índice Herfindahl-Hirschman            │
  │      • Volatilidade de preços                       │
  │      • Score global ponderado 0–10                  │
  └──────────────┬──────────────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────────────┐
  │  [5] PESQUISA DE INFRAESTRUTURA                     │
  │      • Usuário informa tipo: VPS, Docker, K8s, etc. │
  │      • Busca preços atuais de provedores na web     │
  │      • Compara: Contabo, Hetzner, Hostinger, OVH,   │
  │        Railway, Render, Fly.io, DigitalOcean, etc.  │
  │      • Seleciona menor custo p/ RAM necessária      │
  └──────────────┬──────────────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────────────┐
  │  [6] CÁLCULOS FINANCEIROS (NumPy/SciPy)             │
  │      • Investimento inicial e capital de giro       │
  │      • Break-even (ponto de equilíbrio)             │
  │      • Payback simples                              │
  │      • VPL e TIR (projeção 5 anos)                  │
  │      • LTV, CAC, Churn, razão LTV/CAC               │
  │      • Projeção mensal de escala (12 meses)         │
  └──────────────┬──────────────────────────────────────┘
                 │
                 ▼
         relatorio_financeiro.html
         relatorio_validacao.json
```

---

## Pré-requisitos

- Python 3.10+
- Chave de API DeepSeek (gratuita para baixo volume): [platform.deepseek.com](https://platform.deepseek.com)
- (Opcional) Instância SearXNG auto-hospedada para busca sem rate-limit

## Instalação

```bash
git clone https://github.com/IA-PlayGround/calculo.git
cd calculo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Preencha DEEPSEEK_API_KEY no .env
```

## Configuração

```env
# .env
DEEPSEEK_API_KEY=sua-chave-aqui
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_URL=https://api.deepseek.com/v1/chat/completions

# Opcional — SearXNG evita rate-limit do DuckDuckGo
SEARXNG_URL=http://localhost:8080
```

---

## Modos de uso

### 1. Análise de projeto (diretório)

O modo principal. Detecta toda a stack do projeto, pede concorrentes e tipo de infraestrutura interativamente, pesquisa provedores e gera o relatório completo.

```bash
python main.py --dir /caminho/do/projeto
```

O sistema perguntará interativamente:

```
─────────────────────────────────────────────────────
  CONFIGURAÇÃO DA ANÁLISE
─────────────────────────────────────────────────────

[CONCORRENTES]
  Liste os concorrentes do projeto separados por vírgula.
  Exemplo: Stripe, PagSeguro, Asaas, Mercado Pago
  Pressione ENTER para busca automática por concorrentes.
  Concorrentes: Stripe, PagSeguro, Asaas

[INFRAESTRUTURA]
  1. VPS (Servidor Virtual Privado)
  2. VPS + Docker
  3. Docker Swarm / Portainer
  4. Kubernetes Gerenciado
  5. Serverless / FaaS
  6. PaaS (Railway / Render / Fly.io)
  7. Bare Metal Dedicado

  Tipo de infraestrutura [1-7, padrão=1]: 2

[ESCALA]
  Número inicial de clientes/usuários [padrão=5]: 10
  Meta de clientes em 12 meses [padrão=50]: 100
```

Ou passe tudo via flags:

```bash
python main.py --dir ./meu-projeto \
               --concorrentes "Stripe,PagSeguro,Asaas" \
               --infra docker \
               --escala 10:100
```

**Tipos de infraestrutura disponíveis:**

| Flag | Descrição | Provedores pesquisados |
|------|-----------|----------------------|
| `vps` | VPS Linux padrão | Contabo, Hetzner, Hostinger, OVH, Vultr, DigitalOcean |
| `docker` | VPS + Docker Engine | Contabo, Hetzner, Hostinger, DigitalOcean |
| `swarm` | Docker Swarm multi-nó | Hetzner ×3, Contabo ×3, Hostinger ×3 |
| `k8s` | Kubernetes gerenciado | Hetzner K3s, DigitalOcean K8s, GKE, EKS |
| `serverless` | Funções serverless | Cloudflare Workers, Vercel, Netlify, AWS Lambda |
| `paas` | Plataforma gerenciada | Railway, Render, Fly.io, Heroku |
| `bare` | Servidor dedicado | OVHcloud, Hetzner AX, Contabo Bare Metal |

### 2. Análise de URL

Extrai conteúdo de um site SaaS, identifica features, concorrentes e preços automaticamente.

```bash
python main.py https://minha-startup.com.br
python main.py https://minha-startup.com.br --concorrentes "Concorrente A,Concorrente B"
```

### 3. Análise de ideia (texto)

Para validar uma ideia ainda não desenvolvida.

```bash
python main.py ideia.txt
```

Formato do arquivo:

```
Quero criar um sistema de gestão financeira para MEIs no Brasil,
cobrando R$ 49,90/mês, focado em emissão de notas e controle de caixa.
```

---

## Saídas geradas

| Arquivo | Descrição |
|---------|-----------|
| `relatorio_financeiro.html` | Relatório visual interativo com gauge de risco, gráficos SVG, tabelas de provedores e projeções financeiras |
| `relatorio_validacao.json` | Dados brutos completos da análise em JSON |

### Conteúdo do relatório HTML

- **Gauge de risco** (0–100, estilo Serasa com zonas verde/amarelo/vermelho)
- **Resumo executivo** — investimento, custo mensal, break-even, lucro, LTV/CAC, VPL
- **Investimento inicial** — desenvolvimento, fixo, pré-operacional, capital de giro
- **Precificação** — markup, margem de contribuição, índice MC
- **Viabilidade** — ponto de equilíbrio, payback em 2 cenários
- **VPL e TIR** — projeção de 5 anos a 12% a.a. de taxa de desconto
- **Performance Ano 1** — DRE simplificado com impostos Simples Nacional
- **Métricas SaaS** — LTV, CAC, Churn, razão LTV/CAC
- **Projeção 12 meses** — tabela e gráfico de escala cliente a cliente
- **Matriz de risco** — breakdown dos 4 componentes com pesos

---

## Métricas de risco calculadas

### Score de Risco Global (0–10)

```
Score = Concorrência × 0,30
      + Preço (Z-Score) × 0,30
      + HHI / 1000 × 0,25
      + Volatilidade × 0,15
```

| Score | Parecer |
|-------|---------|
| 0–2 | Risco muito baixo — condições ideais para entrada |
| 2–4 | Risco baixo — mercado favorável |
| 4–7 | Risco moderado — diferenciação necessária |
| 7–10 | Alto risco — desaconselhável sem diferenciação clara |

### HHI — Herfindahl-Hirschman Index

Mede concentração do mercado com base nos players detectados:

| HHI | Classificação |
|-----|---------------|
| > 2500 | Altamente concentrado |
| 1500–2500 | Moderadamente concentrado |
| 1000–1500 | Pouco concentrado |
| < 1000 | Desconcentrado (oportunidade) |

### Z-Score de Preço

Calcula quantos desvios padrão o preço proposto está da média de mercado encontrada nas buscas.

---

## Seleção de provedores de infraestrutura

O sistema detecta automaticamente a RAM necessária para o projeto com base na stack:

| Componente | RAM estimada |
|------------|-------------|
| Next.js (2 workers) | 1.600 MB |
| Fastify + BullMQ | 800 MB |
| PostgreSQL (shared_buffers) | 1.200 MB |
| Redis | 400 MB |
| WhatsApp/Twilio (base) | 300 MB |
| OS + Nginx | 550 MB |

Após detectar a RAM total, o sistema busca na web os preços atuais dos provedores e lista os 5 melhores custo-benefício para o tipo de infraestrutura escolhido, ordenados por preço/mês.

**Exemplo de saída:**

```
TOP PROVEDORES para VPS + Docker:
  1. Contabo VPS S (Docker)           R$    38/mês  (4 vCPU, 8GB RAM)
  2. Hetzner CX32 (Docker)            R$    78/mês  (4 vCPU, 8GB RAM)
  3. Hostinger KVM 2 (Docker)         R$    78/mês  (4 vCPU, 8GB RAM)
  4. Hetzner CX42 (Docker)            R$   154/mês  (8 vCPU, 16GB RAM)
  5. Hostinger KVM 4 (Docker)         R$   150/mês  (4 vCPU, 16GB RAM)
```

---

## Arquitetura dos módulos

```
calculo/
├── main.py               # Ponto de entrada; 3 modos + prompts interativos
├── config.py             # Variáveis de ambiente (.env)
├── llm_extractor.py      # Chamadas ao DeepSeek — extração de parâmetros e semântica
├── web_search.py         # SearXNG + DuckDuckGo — busca de mercado e provedores
├── risk_engine.py        # Cálculos de risco: HHI, Z-Score, score global
├── project_analyzer.py   # Análise de diretório, estimativa de RAM, tabela de provedores
├── financial_engine.py   # VPL, TIR, break-even, payback, LTV/CAC, projeção de escala
├── report_generator.py   # Gerador de HTML com SVG (gauge, gráficos de barras)
├── requirements.txt
├── .env.example
└── .gitignore
```

### `llm_extractor.py`

| Função | Entrada | Saída |
|--------|---------|-------|
| `extrair_parametros_ia(texto)` | Descrição da ideia | `{termo_busca, preco_estimado, nicho, regiao, palavras_chave}` |
| `resumir_features_site(html)` | Conteúdo HTML | `{nome_produto, features, preco, nicho, diferenciais}` |
| `analisar_semantica_projeto(analise)` | Dict da stack | `{descricao, tipo_produto, nicho, modelo_negocio, preco_estimado, termo_busca}` |

### `project_analyzer.py`

| Função | Descrição |
|--------|-----------|
| `analisar_diretorio_projeto(path)` | Detecta linguagens, frameworks, DBs, serviços, conta arquivos/linhas, estima RAM |
| `selecionar_provedores(tipo, ram_mb, precos_web)` | Filtra e ordena provedores por RAM e preço |
| `calcular_custos_infra(recursos, tipo_infra, clientes_ini, clientes_meta, precos_web)` | Calcula custos totais anuais e projeção financeira por tipo de infra |

### `risk_engine.py`

| Função | Descrição |
|--------|-----------|
| `calcular_risco_concorrencia(snippets, nicho)` | Conta termos de competição nos snippets |
| `calcular_risco_preco(proposto, concorrentes)` | Z-Score do preço vs. mercado |
| `calcular_hhi(entidades)` | Índice de concentração de mercado |
| `calcular_risco_global(...)` | Ponderação dos 4 fatores → score 0–10 |

### `financial_engine.py`

| Função | Descrição |
|--------|-----------|
| `calcular_investimento_inicial(infra_anual)` | Capital de giro + fixos + pré-operacional |
| `calcular_precificacao(preco, custo_fixo, custo_var)` | Markup e margem de contribuição |
| `calcular_ponto_equilibrio(custo_fixo, preco, custo_var)` | Break-even em clientes e receita |
| `calcular_payback(investimento, clientes, preco, ...)` | Retorno do investimento em meses |
| `calcular_vpl_tir(investimento, fluxos, taxa)` | VPL e TIR por busca binária |
| `calcular_performance(faturamento, custos, impostos)` | DRE simplificado + ROI |
| `calcular_metricas_cliente(...)` | LTV, CAC, Churn, razão LTV/CAC |
| `calcular_metricas_escala(ini, meta, preco, ...)` | Projeção crescimento mensal |

---

## Dependências

```
requests>=2.31.0        # HTTP
numpy>=1.26.0           # Vetores e estatística
scipy>=1.11.0           # Stats avançado (se estendido)
python-dotenv>=1.0.0    # Variáveis de ambiente
duckduckgo-search>=7.0.0 # Busca web fallback
beautifulsoup4>=4.12.0  # Parsing HTML
```

---

## Exemplos de uso completo

```bash
# Analisar projeto Next.js + Fastify com Docker
python main.py --dir ~/projetos/meu-saas --infra docker --escala 5:100

# Analisar startup de fintech com concorrentes conhecidos
python main.py --dir ~/projetos/fintech \
               --concorrentes "Asaas,Iugu,PagSeguro,Stripe" \
               --infra k8s --escala 20:500

# Validar ideia antes de desenvolver
echo "App de agendamento para barbearias, R$ 79/mês, foco em SP" > ideia.txt
python main.py ideia.txt

# Analisar landing page de concorrente
python main.py https://concorrente.com.br --concorrentes "Outro,Terceiro"
```

---

## Licença

MIT
