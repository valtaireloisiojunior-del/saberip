#!/usr/bin/env python3
"""
Agente de geracao de artigos SEO para o SEUIP.ORG
Roda automaticamente via GitHub Actions todo dia.
Gera artigos otimizados com HTML completo, Schema.org, Open Graph, etc.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

# ============ CONFIG ============
TOPICS_FILE = Path(__file__).parent / "topics.json"
TRACKER_FILE = Path(__file__).parent / ".published_tracker.json"
COMMIT_MSG_FILE = Path(__file__).parent / ".last_commit_msg"
BLOG_DIR = Path(__file__).parent.parent / "blog"
BASE_URL = "https://seuip.org"
GA_ID = "G-MCNWEQ8XMH"
ADSENSE_CLIENT = "ca-pub-2713105320249369"


def load_topics():
    """Carrega banco de topicos."""
    if not TOPICS_FILE.exists():
        print("ERRO: topics.json nao encontrado!")
        sys.exit(1)
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tracker():
    """Carrega tracker de artigos ja publicados."""
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"published": [], "last_date": ""}


def save_tracker(tracker):
    """Salva tracker."""
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)


def select_topic(topics, tracker, force_index=None):
    """Escolhe o proximo topico nao publicado."""
    published_slugs = {p["slug"] for p in tracker["published"]}

    if force_index is not None:
        idx = int(force_index) % len(topics)
        return topics[idx], idx

    for i, topic in enumerate(topics):
        if topic["slug"] not in published_slugs:
            return topic, i

    # Todos publicados, reseta e comeca de novo
    print("Todos os topicos foram publicados! Reiniciando ciclo...")
    tracker["published"] = []
    return topics[0], 0


def generate_with_gemini(topic):
    """Gera artigo usando API do Gemini (gratuita)."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    prompt = f"""Voce e um redator SEO especialista em tecnologia. Escreva um artigo completo em portugues do Brasil sobre:

TITULO: {topic['title']}
DESCRICAO: {topic['description']}
KEYWORDS: {', '.join(topic['keywords'])}
CATEGORIA: {topic['category']}

REGRAS:
- Artigo completo com 1500-2500 palavras
- Tom informativo e acessivel
- Use subtitulos H2 e H3
- Inclua listas, tabelas e exemplos praticos
- Adicione uma secao "FAQ" com 5 perguntas e respostas
- Adicione uma "Conclusao" no final
- Use negrito em palavras-chave importantes
- NAO use markdown, use HTML puro com tags <p>, <h2>, <h3>, <ul>, <li>, <table>, <tr>, <td>, <th>, <strong>, <code>
- O conteudo deve ser original e util para leitores brasileiros
- Inclua dicas praticas e passo a passo quando aplicavel

Retorne APENAS o HTML do conteudo do artigo (sem head, body, html tags - apenas o conteudo dentro de <article>)."""

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 8192,
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=120)
        data = resp.json()
        if "candidates" in data and data["candidates"]:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            # Remove markdown code blocks if present
            content = re.sub(r'^```html\s*', '', content)
            content = re.sub(r'\s*```\s*$', '', content)
            return content.strip()
    except Exception as e:
        print(f"Erro Gemini: {e}")
    return None


def generate_with_openai(topic):
    """Gera artigo usando API OpenAI."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""Voce e um redator SEO especialista. Escreva um artigo completo em portugues do Brasil sobre:

TITULO: {topic['title']}
DESCRICAO: {topic['description']}
KEYWORDS: {', '.join(topic['keywords'])}

REGRAS:
- 1500-2500 palavras
- Subtitulos H2 e H3
- Listas, tabelas, exemplos praticos
- Secao FAQ com 5 perguntas
- Conclusao no final
- Use HTML puro: <p>, <h2>, <h3>, <ul>, <li>, <table>, <tr>, <td>, <th>, <strong>, <code>
- Retorne APENAS o HTML do conteudo (dentro de <article>)
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 4000
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        data = resp.json()
        if "choices" in data:
            content = data["choices"][0]["message"]["content"]
            content = re.sub(r'^```html\s*', '', content)
            content = re.sub(r'\s*```\s*$', '', content)
            return content.strip()
    except Exception as e:
        print(f"Erro OpenAI: {e}")
    return None


def generate_fallback_article(topic):
    """Artigo de fallback caso as APIs falhem."""
    kw = topic['keywords'][0] if topic['keywords'] else topic['title']
    return f"""<h1>{topic['title']}</h1>
<p>Neste guia completo, vamos explorar tudo sobre <strong>{topic['title']}</strong>. Voce vai aprender os conceitos fundamentais, dicas praticas e como aplicar no seu dia a dia.</p>

<div class="cta-box">
    <h3>🚀 Quer testar agora?</h3>
    <p>Acesse nossa ferramenta gratuita e facil de usar.</p>
    <a href="{topic.get('tool_link', '/')}" class="cta-btn">Acessar Ferramenta</a>
</div>

<h2>O que e {kw}?</h2>
<p><strong>{topic['title']}</strong> e um tema essencial para quem trabalha com tecnologia no Brasil. Entender como funciona pode economizar horas de trabalho e evitar problemas comuns.</p>

<h2>Por que isso importa?</h2>
<ul>
    <li><strong>Facilidade:</strong> Processos simples e diretos</li>
    <li><strong>Seguranca:</strong> Melhores praticas recomendadas</li>
    <li><strong>Velocidade:</strong> Resultados em segundos, nao em horas</li>
    <li><strong>Gratuito:</strong> Ferramentas acessiveis a todos</li>
</ul>

<h2>Passo a passo completo</h2>
<ol>
    <li><strong>Acesse a ferramenta</strong> — Clique no link acima ou navegue pelo menu</li>
    <li><strong>Preencha os dados</strong> — Insira as informacoes solicitadas nos campos</li>
    <li><strong>Clique em gerar/validar</strong> — O resultado aparece instantaneamente</li>
    <li><strong>Copie ou salve</strong> — Use o resultado conforme sua necessidade</li>
</ol>

<h2>Tabela comparativa</h2>
<table>
<tr><th>Metodo</th><th>Tempo</th><th>Custo</th><th>Qualidade</th></tr>
<tr><td>Ferramenta online</td><td>Segundos</td><td>Gratis</td><td>Alta</td></tr>
<tr><td>Manual</td><td>Minutos</td><td>Gratis</td><td>Media</td></tr>
<tr><td>Software pago</td><td>Minutos</td><td>R$ 50-200/mes</td><td>Alta</td></tr>
</table>

<h2>Dicas profissionais</h2>
<ul>
    <li>Sempre <strong>verifique os resultados</strong> antes de usar em producao</li>
    <li>Guie seus dados em local seguro para consultas futuras</li>
    <li>Mantenha suas ferramentas atualizadas</li>
    <li>Compartilhe com sua equipe para padronizar processos</li>
</ul>

<h2>FAQ — Duvidas Frequentes</h2>
<div class="faq-item">
    <h3>E gratis usar?</h3>
    <p>Sim! Todas as ferramentas do SEUIP.ORG sao 100% gratuitas e sem limite de uso.</p>
</div>
<div class="faq-item">
    <h3>Preciso criar conta?</h3>
    <p>Nao. Nenhuma ferramenta exige cadastro ou login. Use direto pelo navegador.</p>
</div>
<div class="faq-item">
    <h3>Funciona no celular?</h3>
    <p>Sim, todas as ferramentas sao responsivas e funcionam perfeitamente em smartphones e tablets.</p>
</div>
<div class="faq-item">
    <h3>Os dados sao seguros?</h3>
    <p>Sim. Nao armazenamos nenhuma informacao em nossos servidores. Tudo processado localmente no seu navegador.</p>
</div>
<div class="faq-item">
    <h3>Posso usar para trabalho profissional?</h3>
    <p>Com certeza! Muitos desenvolvedores, contadores e profissionais de TI usam diariamente.</p>
</div>

<h2>Conclusao</h2>
<p><strong>{topic['title']}</strong> e uma habilidade essencial na era digital. Com as ferramentas certas, voce economiza tempo, evita erros e trabalha com mais eficiencia. Explore todas as ferramentas disponiveis no <a href="/">SEUIP.ORG</a> e descubra como simplificar suas tarefas diarias.</p>
"""


def build_html(article_content, topic, date_str, related, tools):
    """Monta o HTML completo do artigo com SEO."""
    slug = topic["slug"]
    title = topic["title"]
    desc = topic["description"]
    keywords = ", ".join(topic["keywords"])
    category = topic.get("category", "Tecnologia")
    emoji = topic.get("emoji", "📝")
    reading_time = topic.get("reading_time", "5 min")

    related_html = "\n".join(
        f'                    <li><a href="{r["link"]}">→ {r["title"]}</a></li>'
        for r in related
    )
    tools_html = "\n".join(
        f'                    <li><a href="{t["link"]}">→ {t["title"]}</a></li>'
        for t in tools
    )

    # Gera nomes de slots unicos para AdSense
    ad_slot_article = f"{slug[:20]}-inarticle"
    ad_slot_sidebar = f"{slug[:20]}-sidebar"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#00ff99">
    <title>{title} | SEUIP.ORG</title>
    <meta name="description" content="{desc}">
    <link rel="canonical" href="{BASE_URL}/blog/{slug}.html">
    <meta name="keywords" content="{keywords}">
    <meta name="author" content="SEUIP.ORG">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{BASE_URL}/blog/{slug}.html">
    <meta property="og:site_name" content="SEUIP.ORG">
    <meta property="article:published_time" content="{date_str}">
    <meta property="article:section" content="{category}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{desc}">
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>
    <script type="application/ld+json">
{{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "description": "{desc}",
    "url": "{BASE_URL}/blog/{slug}.html",
    "datePublished": "{date_str}",
    "dateModified": "{date_str}",
    "author": {{"@type": "Organization", "name": "SEUIP.ORG"}},
    "publisher": {{"@type": "Organization", "name": "SEUIP.ORG"}},
    "articleSection": "{category}",
    "keywords": "{keywords}"
}}
    </script>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
        :root{{--primary:#00ff99;--primary-dark:#00cc77;--bg:#0d0d0d;--bg-card:#1a1a1a;--bg-elevated:#222;--text:#fff;--text-secondary:#aaa;--border:#333;--radius:12px;--radius-sm:8px;--transition:all 0.3s ease}}
        body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.7;min-height:100vh}}
        .header{{text-align:center;padding:1.5rem 1rem;background:linear-gradient(180deg,rgba(0,255,153,0.1) 0%,transparent 100%);border-bottom:1px solid var(--border);position:relative}}
        .header::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--primary),transparent)}}
        .logo{{font-size:2rem;font-weight:900;color:var(--primary);text-decoration:none;display:block;letter-spacing:-1px}}
        .tagline{{color:var(--text-secondary);font-size:0.9rem;margin-top:0.5rem}}
        .container{{max-width:800px;margin:0 auto;padding:2rem 1rem}}
        .breadcrumb{{display:flex;gap:0.5rem;align-items:center;margin-bottom:1.5rem;font-size:0.85rem;color:var(--text-secondary);flex-wrap:wrap}}
        .breadcrumb a{{color:var(--primary);text-decoration:none}}
        h1{{font-size:1.8rem;color:var(--primary);margin-bottom:1rem;line-height:1.3}}
        h2{{font-size:1.3rem;color:var(--primary);margin:2rem 0 1rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border)}}
        h3{{font-size:1.1rem;color:var(--text);margin:1.5rem 0 0.75rem}}
        p{{margin-bottom:1rem;color:var(--text-secondary);line-height:1.8}}
        p strong{{color:var(--text)}}
        ul,ol{{margin:1rem 0 1rem 1.5rem;color:var(--text-secondary)}}
        li{{margin-bottom:0.5rem;line-height:1.7}}
        a{{color:var(--primary);text-decoration:none}}
        .cta-box{{background:linear-gradient(135deg,rgba(0,255,153,0.1),rgba(0,255,153,0.03));border:1px solid rgba(0,255,153,0.3);border-radius:var(--radius);padding:1.5rem;margin:2rem 0;text-align:center}}
        .cta-box h3{{color:var(--primary);margin-bottom:0.75rem}}
        .cta-box p{{color:var(--text);margin-bottom:1rem}}
        .cta-btn{{display:inline-block;background:var(--primary);color:var(--bg);padding:0.8rem 2rem;border-radius:var(--radius-sm);font-weight:700;text-decoration:none;transition:var(--transition);border:none;cursor:pointer;font-size:1rem}}
        .cta-btn:hover{{background:var(--primary-dark);transform:translateY(-2px)}}
        code{{background:rgba(0,255,153,0.1);color:var(--primary);padding:0.2rem 0.5rem;border-radius:4px;font-family:'Courier New',monospace;font-size:0.9rem}}
        pre{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1rem;overflow-x:auto;margin:1rem 0}}
        table{{width:100%;border-collapse:collapse;margin:1rem 0;background:var(--bg-card);border-radius:var(--radius-sm);overflow:hidden;font-size:0.9rem}}
        th{{background:rgba(0,255,153,0.1);color:var(--primary);padding:0.75rem;text-align:left;font-weight:600;border-bottom:1px solid var(--border)}}
        td{{padding:0.75rem;border-bottom:1px solid var(--border);color:var(--text-secondary)}}
        .faq-item{{margin-bottom:1.5rem;padding:1rem;background:var(--bg-card);border-radius:var(--radius-sm);border:1px solid var(--border)}}
        .faq-item h3{{color:var(--primary);font-size:1.05rem;margin:0;cursor:pointer}}
        .faq-item p{{margin-top:0.5rem;margin-bottom:0}}
        .reading-time{{color:var(--text-secondary);font-size:0.85rem;margin-bottom:1.5rem}}
        .sidebar-box{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:1.2rem;margin-bottom:1rem}}
        .sidebar-box h4{{color:var(--primary);font-size:0.95rem;margin-bottom:0.75rem}}
        .sidebar-box ul{{list-style:none;margin:0;padding:0}}
        .sidebar-box li{{margin-bottom:0.5rem}}
        .sidebar-box a{{font-size:0.9rem;color:var(--text-secondary);text-decoration:none}}
        .sidebar-box a:hover{{color:var(--primary)}}
        .ad-box{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:1rem;margin:1.5rem 0;text-align:center;min-height:90px;display:flex;align-items:center;justify-content:center;color:var(--text-secondary);font-size:0.85rem}}
        .footer{{text-align:center;padding:2rem 1rem;margin-top:3rem;border-top:1px solid var(--border);color:var(--text-secondary);font-size:0.85rem}}
        .footer-links{{display:flex;justify-content:center;flex-wrap:wrap;gap:0.75rem;margin-bottom:1rem}}
        .footer-links a{{color:var(--primary);font-weight:600;padding:0.3rem 0.6rem;background:rgba(0,255,153,0.1);border-radius:6px;font-size:0.85rem;text-decoration:none}}
        @media(min-width:900px){{.layout{{display:grid;grid-template-columns:1fr 270px;gap:2rem;max-width:1100px;margin:0 auto}}.container{{max-width:none;padding:2rem 0}}}}
        @media(max-width:640px){{h1{{font-size:1.4rem}}}}
    </style>
</head>
<body>
    <header class="header">
        <a href="/" class="logo">🌐 SEUIP.ORG</a>
        <p class="tagline">Blog — {category}</p>
    </header>
    <div class="layout">
        <div class="container">
            <nav class="breadcrumb"><a href="/">Inicio</a><span>/</span><a href="/blog/">Blog</a><span>/</span><span>{title.split(' — ')[0].split(' [')[0][:40]}</span></nav>
            <div class="reading-time">⏱️ {reading_time} de leitura | 📅 Atualizado em {date_str}</div>
            <article>
                {article_content}
            </article>
            <div class="ad-box">
                <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ad_slot_article}" data-ad-format="auto" data-full-width-responsive="true"></ins>
                <script>(adsbygoogle=window.adsbygoogle||[]).push({{}})</script>
            </div>
        </div>
        <aside style="padding:2rem 1rem">
            <div class="sidebar-box">
                <h4>📚 Artigos relacionados</h4>
                <ul>
{related_html}
                </ul>
            </div>
            <div class="sidebar-box">
                <h4>🛠️ Ferramentas</h4>
                <ul>
{tools_html}
                </ul>
            </div>
            <div class="ad-box" style="min-height:250px">
                <ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ad_slot_sidebar}" data-ad-format="auto" data-full-width-responsive="true"></ins>
                <script>(adsbygoogle=window.adsbygoogle||[]).push({{}})</script>
            </div>
        </aside>
    </div>
    <footer class="footer">
        <div class="footer-links">
            <a href="/">🏠 Inicio</a>
            <a href="/blog/">📝 Blog</a>
            <a href="/monetizacao.html">💰 Monetizacao</a>
            <a href="/termos.html">📋 Termos</a>
        </div>
        <p>© {datetime.now().year} SEUIP.ORG — Ferramentas e utilitarios online</p>
    </footer>
</body>
</html>"""


def update_blog_index(topic, date_str):
    """Adiciona novo artigo ao blog/index.html."""
    index_path = BLOG_DIR / "index.html"
    if not index_path.exists():
        print(f"AVISO: {index_path} nao existe. Pulando atualizacao do index.")
        return

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    emoji = topic.get("emoji", "📝")
    slug = topic["slug"]
    title = topic["title"].split(" | ")[0].split(" [")[0]
    desc = topic["description"][:100] + "..." if len(topic["description"]) > 100 else topic["description"]
    reading_time = topic.get("reading_time", "5 min")
    category = topic.get("category", "Tecnologia")

    new_card = f"""<a href="{slug}.html" class="post-card"><div class="post-emoji">{emoji}</div><div class="post-content"><span class="post-title">{title}</span><p class="post-desc">{desc}</p><div class="post-meta"><span>⏱️ {reading_time}</span><span class="post-tag">{category}</span></div></div></a>
"""

    # Insere apos <div class="post-list">
    insert_marker = '<div class="post-list">\n'
    if insert_marker in content:
        content = content.replace(insert_marker, insert_marker + new_card)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Index atualizado com: {title}")
    else:
        print("AVISO: Nao foi possivel encontrar marcador no index.html")


def update_sitemap(slug, date_str):
    """Adiciona nova URL ao sitemap.xml."""
    sitemap_path = Path(__file__).parent.parent / "sitemap.xml"
    if not sitemap_path.exists():
        return

    with open(sitemap_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_url = f"""  <url>
    <loc>{BASE_URL}/blog/{slug}.html</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
"""

    insert_marker = "</urlset>"
    if insert_marker in content:
        content = content.replace(insert_marker, new_url + insert_marker)
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Sitemap atualizado com: {slug}")


def main():
    print("=" * 50)
    print("AGENTE DE ARTIGOS SEUIP.ORG")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    topics = load_topics()
    tracker = load_tracker()
    force_index = os.environ.get("TOPIC_INDEX", "").strip() or None

    topic, idx = select_topic(topics, tracker, force_index)
    print(f"\nTopico selecionado [{idx}]: {topic['title']}")

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Tenta gerar com IA
    print("\nGerando artigo com IA...")
    article_html = None

    if os.environ.get("GEMINI_API_KEY"):
        article_html = generate_with_gemini(topic)
        if article_html:
            print("✅ Artigo gerado com Gemini")

    if not article_html and os.environ.get("OPENAI_API_KEY"):
        article_html = generate_with_openai(topic)
        if article_html:
            print("✅ Artigo gerado com OpenAI")

    if not article_html:
        print("⚠️ APIs de IA indisponiveis. Usando template fallback.")
        article_html = generate_fallback_article(topic)

    # Artigo precisa estar dentro de <article> ja
    if not article_html.startswith("<h1>"):
        article_html = f"<h1>{topic['title'].split(' | ')[0]}</h1>\n" + article_html

    # Monta relacionados e ferramentas
    related = topic.get("related", [
        {"title": "Como Descobrir Meu IP", "link": "/blog/como-descobrir-meu-ip.html"},
        {"title": "Como Gerar CPF Valido", "link": "/blog/como-gerar-cpf-valido.html"},
    ])
    tools = topic.get("tools", [
        {"title": "Ferramentas Online", "link": "/"},
        {"title": "Meu IP", "link": "/meu-ip.html"},
    ])

    # Gera HTML completo
    full_html = build_html(article_html, topic, date_str, related, tools)

    # Salva arquivo
    output_file = BLOG_DIR / f"{topic['slug']}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"\n✅ Artigo salvo: {output_file}")

    # Atualiza blog index
    update_blog_index(topic, date_str)

    # Atualiza sitemap
    update_sitemap(topic["slug"], date_str)

    # Atualiza tracker
    tracker["published"].append({
        "slug": topic["slug"],
        "title": topic["title"],
        "date": date_str
    })
    tracker["last_date"] = date_str
    save_tracker(tracker)

    # Commit message
    commit_msg = f"Add article: {topic['slug']} - {date_str}"
    with open(COMMIT_MSG_FILE, "w", encoding="utf-8") as f:
        f.write(commit_msg)

    print(f"\n{'=' * 50}")
    print(f"✅ ARTIGO PUBLICADO: {topic['title']}")
    print(f"🔗 URL: {BASE_URL}/blog/{topic['slug']}.html")
    print(f"📅 Data: {date_str}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
