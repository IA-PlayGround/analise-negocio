import os
import json
import re
import subprocess
from pathlib import Path


FRAMEWORKS_MAP = {
    "next": "Next.js",
    "react": "React",
    "vue": "Vue.js",
    "angular": "Angular",
    "fastify": "Fastify",
    "express": "Express",
    "nestjs": "NestJS",
    "prisma": "Prisma ORM",
    "drizzle": "Drizzle ORM",
    "tailwindcss": "Tailwind CSS",
    "zustand": "Zustand",
    "socket.io": "Socket.IO",
    "bullmq": "BullMQ",
    "ioredis": "Redis",
    "stripe": "Stripe",
    "twilio": "Twilio",
    "puppeteer": "Puppeteer",
    "@google/generative-ai": "Google Gemini AI",
    "openai": "OpenAI",
}

BANCOS_MAP = {
    "postgres": "PostgreSQL",
    "pg": "PostgreSQL",
    "mysql2": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "ioredis": "Redis",
}


def analisar_diretorio_projeto(caminho: str) -> dict:
    raiz = Path(caminho).resolve()
    if not raiz.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {caminho}")

    resultado = {
        "caminho": str(raiz),
        "nome": raiz.name,
        "linguagens": {},
        "frameworks": [],
        "bancos": [],
        "servicos_externos": [],
        "infra": [],
        "total_arquivos": 0,
        "total_linhas": 0,
        "estimativa_recursos": {},
    }

    # Detect technologies from files
    for pkg_path in [raiz / "package.json", raiz / "api" / "package.json"]:
        if pkg_path.exists():
            try:
                with open(pkg_path) as f:
                    pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                for dep, tech in FRAMEWORKS_MAP.items():
                    if dep in deps and tech not in resultado["frameworks"]:
                        resultado["frameworks"].append(tech)
                for dep, tech in BANCOS_MAP.items():
                    if dep in deps and tech not in resultado["bancos"]:
                        resultado["bancos"].append(tech)
                resultado["linguagens"]["JavaScript/TypeScript"] = True
            except Exception:
                pass

    # Check Python
    if list(raiz.glob("*.py")) or (raiz / "requirements.txt").exists():
        resultado["linguagens"]["Python"] = True

    # Check Go
    if (raiz / "go.mod").exists():
        resultado["linguagens"]["Go"] = True

    # Check Rust
    if (raiz / "Cargo.toml").exists():
        resultado["linguagens"]["Rust"] = True

    # Detect Docker
    if (raiz / "Dockerfile").exists():
        resultado["infra"].append("Docker")
    if (raiz / "docker-compose.yml").exists() or (raiz / "docker-compose.yaml").exists():
        resultado["infra"].append("Docker Compose")

    # Detect Nginx
    if list(raiz.glob("**/nginx*.conf")):
        resultado["infra"].append("Nginx")

    # Detect external services from env files
    for env_file in raiz.glob("**/.env*"):
        try:
            with open(env_file) as f:
                content = f.read()
            servicos_map = {
                "DATABASE_URL": "PostgreSQL (nuvem)",
                "REDIS_URL": "Redis",
                "UPSTASH": "Upstash Redis",
                "NEON": "Neon PostgreSQL",
                "SUPABASE": "Supabase",
                "STRIPE": "Stripe",
                "MERCADO_PAGO": "Mercado Pago",
                "MP_ACCESS_TOKEN": "Mercado Pago",
                "PAGBANK": "PagBank",
                "TWILIO": "Twilio",
                "RESEND": "Resend",
                "PUSHER": "Pusher",
                "CLOUDINARY": "Cloudinary",
                "SENDGRID": "SendGrid",
                "OPENAI": "OpenAI API",
                "DEEPSEEK": "DeepSeek API",
                "GOOGLE_AI": "Google AI",
                "FACEBOOK_APP": "Facebook OAuth",
                "FOCUS_NFE": "FocusNFe",
                "VERCEL": "Vercel",
            }
            for key, svc in servicos_map.items():
                if key in content and svc not in resultado["servicos_externos"]:
                    resultado["servicos_externos"].append(svc)
        except Exception:
            pass

    # Count files and lines
    extensoes = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".vue", ".css", ".sql", ".prisma", ".yml", ".yaml", ".json"}
    for ext in extensoes:
        for arquivo in raiz.rglob(f"*{ext}"):
            if "node_modules" in str(arquivo) or ".next" in str(arquivo) or "dist" in str(arquivo):
                continue
            resultado["total_arquivos"] += 1
            try:
                with open(arquivo) as f:
                    resultado["total_linhas"] += sum(1 for _ in f)
            except Exception:
                pass

    # Estimate resources per component
    has_nextjs = "Next.js" in resultado["frameworks"]
    has_fastify = "Fastify" in resultado["frameworks"]
    needs_db = any(b in resultado["bancos"] for b in ["PostgreSQL", "MySQL", "MongoDB"])
    needs_redis = "Redis" in resultado["bancos"]
    has_whatsapp = "Twilio" in resultado["servicos_externos"]
    has_realtime = "Socket.IO" in resultado["frameworks"] or "Pusher" in resultado["servicos_externos"]

    # Per-component RAM
    ram_nextjs = 1600 if has_nextjs else 0   # 2 workers × 800MB
    ram_fastify = 800 if has_fastify else 0   # 1 worker + BullMQ + Socket.IO
    ram_postgres = 1200 if needs_db else 0    # shared_buffers=512MB + work_mem
    ram_redis = 400 if needs_redis else 0     # maxmemory 256MB + overhead
    ram_whatsapp_base = 300 if has_whatsapp else 0
    ram_os = 500
    ram_nginx = 50

    ram_base = ram_nextjs + ram_fastify + ram_postgres + ram_redis + ram_whatsapp_base + ram_os + ram_nginx
    ram_recomendada = max(4096, int(ram_base * 1.3))  # 30% headroom, min 4GB

    resultado["estimativa_recursos"] = {
        "componentes": {
            "nextjs_frontend": f"{ram_nextjs}MB (2 workers)",
            "fastify_backend": f"{ram_fastify}MB (1 worker + realtime)",
            "postgresql_local": f"{ram_postgres}MB" if needs_db else "gerenciado (nuvem)",
            "redis_local": f"{ram_redis}MB" if needs_redis else "não",
            "whatsapp_base": f"{ram_whatsapp_base}MB (sessões iniciais)" if has_whatsapp else "não",
            "nginx_sistema": f"{ram_nginx}MB + {ram_os}MB OS",
        },
        "ram_total_mb": ram_base,
        "ram_recomendada_mb": ram_recomendada,
        "cpu_minima": 2 if (has_nextjs and has_fastify) else 1,
        "cpu_recomendada": 4 if has_whatsapp else 2,
        "disco_gb": 50 if needs_db else 30,
        "precisa_db": needs_db,
        "precisa_redis": needs_redis,
        "precisa_whatsapp": has_whatsapp,
        "whatsapp_ram_por_tenant_mb": 150,
    }

    return resultado


INFRA_TIPOS = {
    "vps": "VPS (Servidor Virtual Privado)",
    "docker": "VPS + Docker",
    "swarm": "Docker Swarm / Portainer",
    "k8s": "Kubernetes Gerenciado",
    "serverless": "Serverless / FaaS",
    "paas": "PaaS (Railway / Render / Fly.io)",
    "bare": "Bare Metal Dedicado",
}

INFRA_OVERHEAD_RAM = {
    "vps": 0,
    "docker": 512,
    "swarm": 1024,
    "k8s": 2048,
    "serverless": 0,
    "paas": 0,
    "bare": 0,
}

# Preços de referência em R$/mês (aproximados, câmbio ~5.50 BRL/USD)
PROVEDORES_REFERENCIA: dict[str, list[dict]] = {
    "vps": [
        {"nome": "Contabo VPS S", "vcpu": 4, "ram_gb": 8, "disco_gb": 200, "preco_mes_brl": 38},
        {"nome": "Contabo VPS M", "vcpu": 6, "ram_gb": 16, "disco_gb": 400, "preco_mes_brl": 66},
        {"nome": "Contabo VPS L", "vcpu": 8, "ram_gb": 30, "disco_gb": 400, "preco_mes_brl": 121},
        {"nome": "Hetzner CX22", "vcpu": 2, "ram_gb": 4, "disco_gb": 40, "preco_mes_brl": 42},
        {"nome": "Hetzner CX32", "vcpu": 4, "ram_gb": 8, "disco_gb": 80, "preco_mes_brl": 78},
        {"nome": "Hetzner CX42", "vcpu": 8, "ram_gb": 16, "disco_gb": 160, "preco_mes_brl": 154},
        {"nome": "Hostinger KVM 1", "vcpu": 2, "ram_gb": 4, "disco_gb": 50, "preco_mes_brl": 60},
        {"nome": "Hostinger KVM 2", "vcpu": 4, "ram_gb": 8, "disco_gb": 100, "preco_mes_brl": 78},
        {"nome": "Hostinger KVM 4", "vcpu": 4, "ram_gb": 16, "disco_gb": 200, "preco_mes_brl": 150},
        {"nome": "OVHcloud VPS Value", "vcpu": 1, "ram_gb": 2, "disco_gb": 20, "preco_mes_brl": 25},
        {"nome": "OVHcloud VPS Essential", "vcpu": 2, "ram_gb": 4, "disco_gb": 80, "preco_mes_brl": 50},
        {"nome": "Vultr High Perf 4GB", "vcpu": 2, "ram_gb": 4, "disco_gb": 100, "preco_mes_brl": 132},
        {"nome": "DigitalOcean 4GB", "vcpu": 2, "ram_gb": 4, "disco_gb": 80, "preco_mes_brl": 132},
        {"nome": "DigitalOcean 8GB", "vcpu": 4, "ram_gb": 8, "disco_gb": 160, "preco_mes_brl": 264},
    ],
    "docker": [
        {"nome": "Contabo VPS S (Docker)", "vcpu": 4, "ram_gb": 8, "disco_gb": 200, "preco_mes_brl": 38},
        {"nome": "Contabo VPS M (Docker)", "vcpu": 6, "ram_gb": 16, "disco_gb": 400, "preco_mes_brl": 66},
        {"nome": "Hetzner CX32 (Docker)", "vcpu": 4, "ram_gb": 8, "disco_gb": 80, "preco_mes_brl": 78},
        {"nome": "Hetzner CX42 (Docker)", "vcpu": 8, "ram_gb": 16, "disco_gb": 160, "preco_mes_brl": 154},
        {"nome": "Hostinger KVM 2 (Docker)", "vcpu": 4, "ram_gb": 8, "disco_gb": 100, "preco_mes_brl": 78},
        {"nome": "Hostinger KVM 4 (Docker)", "vcpu": 4, "ram_gb": 16, "disco_gb": 200, "preco_mes_brl": 150},
        {"nome": "DigitalOcean 8GB (Docker)", "vcpu": 4, "ram_gb": 8, "disco_gb": 160, "preco_mes_brl": 264},
    ],
    "swarm": [
        {"nome": "Hetzner CX22 ×3 (Swarm)", "vcpu": 6, "ram_gb": 12, "disco_gb": 120, "preco_mes_brl": 126},
        {"nome": "Contabo VPS S ×3 (Swarm)", "vcpu": 12, "ram_gb": 24, "disco_gb": 600, "preco_mes_brl": 114},
        {"nome": "Hetzner CX32 ×3 (Swarm)", "vcpu": 12, "ram_gb": 24, "disco_gb": 240, "preco_mes_brl": 234},
        {"nome": "Hostinger KVM 2 ×3 (Swarm)", "vcpu": 12, "ram_gb": 24, "disco_gb": 300, "preco_mes_brl": 234},
    ],
    "k8s": [
        {"nome": "Hetzner K3s 2 nós CX22", "vcpu": 4, "ram_gb": 8, "disco_gb": 80, "preco_mes_brl": 84},
        {"nome": "Hetzner K3s 2 nós CX32", "vcpu": 8, "ram_gb": 16, "disco_gb": 160, "preco_mes_brl": 156},
        {"nome": "DigitalOcean K8s 2 nós 4GB", "vcpu": 4, "ram_gb": 8, "disco_gb": 160, "preco_mes_brl": 264},
        {"nome": "DigitalOcean K8s 3 nós 4GB", "vcpu": 6, "ram_gb": 12, "disco_gb": 240, "preco_mes_brl": 396},
        {"nome": "GKE Autopilot (mínimo)", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 550},
        {"nome": "EKS (1 nó t3.medium)", "vcpu": 2, "ram_gb": 4, "disco_gb": 30, "preco_mes_brl": 500},
    ],
    "serverless": [
        {"nome": "Cloudflare Workers Free", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 0},
        {"nome": "Vercel Hobby (gratuito)", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 0},
        {"nome": "Netlify Free", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 0},
        {"nome": "AWS Lambda (baixo uso)", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 15},
        {"nome": "Cloudflare Workers Paid", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 28},
        {"nome": "Vercel Pro", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 110},
        {"nome": "Netlify Pro", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 110},
        {"nome": "AWS Lambda (alto uso)", "vcpu": None, "ram_gb": None, "disco_gb": None, "preco_mes_brl": 200},
    ],
    "paas": [
        {"nome": "Fly.io Hobby", "vcpu": 1, "ram_gb": 0.25, "disco_gb": 3, "preco_mes_brl": 14},
        {"nome": "Railway Starter", "vcpu": None, "ram_gb": 8, "disco_gb": 100, "preco_mes_brl": 28},
        {"nome": "Render Starter", "vcpu": None, "ram_gb": 0.5, "disco_gb": 1, "preco_mes_brl": 39},
        {"nome": "Fly.io Pro", "vcpu": 2, "ram_gb": 1, "disco_gb": 10, "preco_mes_brl": 55},
        {"nome": "Render Standard", "vcpu": None, "ram_gb": 2, "disco_gb": 50, "preco_mes_brl": 110},
        {"nome": "Railway Team", "vcpu": None, "ram_gb": 32, "disco_gb": 200, "preco_mes_brl": 110},
        {"nome": "Heroku Eco", "vcpu": None, "ram_gb": 0.5, "disco_gb": None, "preco_mes_brl": 165},
        {"nome": "Render Pro", "vcpu": None, "ram_gb": 4, "disco_gb": 100, "preco_mes_brl": 220},
    ],
    "bare": [
        {"nome": "OVHcloud Bare Metal Eco", "vcpu": 4, "ram_gb": 32, "disco_gb": 2000, "preco_mes_brl": 385},
        {"nome": "Hetzner AX41", "vcpu": 8, "ram_gb": 64, "disco_gb": 2000, "preco_mes_brl": 462},
        {"nome": "Contabo Bare Metal M", "vcpu": 8, "ram_gb": 64, "disco_gb": 2000, "preco_mes_brl": 550},
        {"nome": "Hetzner AX52", "vcpu": 8, "ram_gb": 128, "disco_gb": 2000, "preco_mes_brl": 770},
    ],
}


def selecionar_provedores(tipo_infra: str, ram_mb: int, precos_web: list[float] | None = None) -> list[dict]:
    """Select and rank providers for the given infra type and RAM requirement."""
    base = list(PROVEDORES_REFERENCIA.get(tipo_infra, PROVEDORES_REFERENCIA["vps"]))
    ram_gb_needed = ram_mb / 1024

    # For infra types where RAM is not the selection criterion
    if tipo_infra in ("serverless", "paas"):
        candidatos = sorted(base, key=lambda p: p["preco_mes_brl"])
    else:
        adequados = [p for p in base if p.get("ram_gb") and p["ram_gb"] >= ram_gb_needed]
        if not adequados:
            adequados = sorted(base, key=lambda p: p.get("ram_gb") or 0, reverse=True)[:3]
        candidatos = sorted(adequados, key=lambda p: p["preco_mes_brl"])

    # If web search found prices lower than our reference, note it
    if precos_web:
        preco_web_min = min(precos_web)
        for p in candidatos:
            if p["preco_mes_brl"] > preco_web_min * 1.2:
                p["nota"] = f"Busca web encontrou preços a partir de R${preco_web_min:.0f}"
                break

    return candidatos


def calcular_custos_infra(
    recursos: dict,
    tipo_infra: str = "vps",
    clientes_ini: int = 5,
    clientes_meta: int = 50,
    precos_web: list[float] | None = None,
) -> dict:
    tipo_infra = tipo_infra.lower()
    comp = recursos.get("componentes", {})
    precisa_db = recursos.get("precisa_db", True)
    precisa_redis = recursos.get("precisa_redis", False)
    precisa_whatsapp = recursos.get("precisa_whatsapp", False)
    whatsapp_ram_tenant = recursos.get("whatsapp_ram_por_tenant_mb", 150)

    ram_base = recursos.get("ram_recomendada_mb", 4096)
    overhead = INFRA_OVERHEAD_RAM.get(tipo_infra, 0)
    ram_ini = ram_base + overhead
    ram_meta = ram_ini + (clientes_meta - clientes_ini) * whatsapp_ram_tenant if precisa_whatsapp else ram_ini

    provedores = selecionar_provedores(tipo_infra, ram_ini, precos_web)
    provedores_meta = selecionar_provedores(tipo_infra, ram_meta, precos_web)

    melhor = provedores[0] if provedores else {"nome": "Indefinido", "preco_mes_brl": 100}
    melhor_meta = provedores_meta[0] if provedores_meta else melhor

    custo_h_mes = melhor["preco_mes_brl"]
    custo_h_ano = round(custo_h_mes * 12, 2)
    custo_meta_mes = melhor_meta["preco_mes_brl"]
    custo_meta_ano = round(custo_meta_mes * 12, 2)

    # External services
    servicos_mes = 0.0
    servicos_detalhe = []
    if precisa_db and tipo_infra not in ("paas",):
        servicos_mes += 50
        servicos_detalhe.append("PostgreSQL gerenciado (Neon/Supabase): R$50")
    if precisa_redis:
        servicos_mes += 12
        servicos_detalhe.append("Redis (Upstash): R$12")
    dominio_mes = 3.33
    servicos_detalhe.append(f"Domínio: R${dominio_mes:.2f}")
    servicos_total_mes = servicos_mes + dominio_mes
    servicos_ano = round(servicos_total_mes * 12, 2)

    total_ano = round(custo_h_ano + servicos_ano, 2)
    total_meta_ano = round(custo_meta_ano + servicos_ano, 2)
    custo_total_mes = custo_h_mes + servicos_total_mes
    custo_por_cliente = round(custo_total_mes / clientes_ini, 2) if clientes_ini > 0 else 0
    custo_por_cliente_meta = round((custo_meta_mes + servicos_total_mes) / clientes_meta, 2) if clientes_meta > 0 else 0

    preco_mes = 99.99
    receita_ini = round(clientes_ini * preco_mes * 12, 2)
    receita_meta = round(clientes_meta * preco_mes * 12, 2)
    lucro_ini = round(receita_ini - total_ano, 2)
    lucro_meta = round(receita_meta - total_meta_ano, 2)

    req_por_cliente_dia = 200

    return {
        "tipo_infra": tipo_infra,
        "tipo_infra_label": INFRA_TIPOS.get(tipo_infra, tipo_infra.upper()),
        "componentes_ram": comp,
        "infraestrutura": {
            "recomendado": melhor["nome"],
            "provedores_top": provedores[:5],
            "custo_mensal": custo_h_mes,
            "custo_anual": custo_h_ano,
            "justificativa": f"RAM estimada: {ram_ini}MB (+{overhead}MB overhead {tipo_infra}) → {melhor['nome']}",
            "servicos_externos": {
                "detalhe": servicos_detalhe,
                "custo_mensal": round(servicos_total_mes, 2),
                "custo_anual": servicos_ano,
            },
            "total_anual": total_ano,
        },
        "escala": {
            "clientes_inicial": clientes_ini,
            "clientes_meta": clientes_meta,
            "ram_inicial_mb": ram_ini,
            "ram_meta_mb": ram_meta,
            "custo_por_cliente_mes": custo_por_cliente,
            "custo_por_cliente_meta_mes": custo_por_cliente_meta,
            "provedor_inicial": melhor["nome"],
            "provedor_meta": melhor_meta["nome"],
            "custo_scale_anual": total_meta_ano,
            "requisicoes": {
                "por_cliente_dia": req_por_cliente_dia,
                "dia_inicial": clientes_ini * req_por_cliente_dia,
                "dia_meta": clientes_meta * req_por_cliente_dia,
                "mes_inicial": clientes_ini * req_por_cliente_dia * 30,
                "mes_meta": clientes_meta * req_por_cliente_dia * 30,
            },
        },
        "projecao_financeira": {
            "preco_por_cliente_mes": preco_mes,
            "receita_anual_inicial": receita_ini,
            "custo_anual_inicial": total_ano,
            "lucro_anual_inicial": lucro_ini,
            "margem_inicial": round(lucro_ini / receita_ini * 100, 1) if receita_ini > 0 else 0,
            "receita_anual_meta": receita_meta,
            "custo_anual_meta": total_meta_ano,
            "lucro_anual_meta": lucro_meta,
            "margem_meta": round(lucro_meta / receita_meta * 100, 1) if receita_meta > 0 else 0,
        },
    }
