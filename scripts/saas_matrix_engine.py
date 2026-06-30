import os
import re
import sys
import json
import argparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup, NavigableString
from openai import OpenAI

# ============================================================
# 1. Configuration
# ============================================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

if not DEEPSEEK_API_KEY:
    print("Error: DEEPSEEK_API_KEY environment variable is required.")
    sys.exit(1)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# Target output directory relative to this script.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "src", "content", "blog")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 2. HTML -> Winner / Verdict Extractor
# ============================================================
def _determine_winner_from_text(text: str, app_a_name: str, app_b_name: str) -> tuple[str, str]:
    """
    Scan a block of text and determine which app is the winner.
    Returns (winner_name, full_text).
    """
    text_lower = text.lower()
    app_a_lower = app_a_name.lower()
    app_b_lower = app_b_name.lower()

    # 1. Explicit "Winner: AppName" or "Verdict: AppName"
    for app_name in [app_a_name, app_b_name]:
        app_lower = app_name.lower()
        patterns = [
            f"winner: {app_lower}",
            f"verdict: {app_lower}",
            f"the verdict: {app_lower}",
            f"**winner:** {app_lower}",
            f"winner is {app_lower}",
            f"choose {app_lower}",
            f"deploy {app_lower}",
        ]
        for pattern in patterns:
            if pattern in text_lower:
                return app_name, text.strip()

    # 2. "Deploy X if..." pattern (the one being deployed is the recommended one)
    deploy_a = text_lower.find(f"deploy {app_a_lower}")
    deploy_b = text_lower.find(f"deploy {app_b_lower}")
    if deploy_a != -1 and deploy_b == -1:
        return app_a_name, text.strip()
    if deploy_b != -1 and deploy_a == -1:
        return app_b_name, text.strip()

    # 3. Superior / definitive choice / best choice near one app name
    superior_keywords = ["superior", "definitive choice", "best choice", "optimal", "recommended", "leads by"]
    for keyword in superior_keywords:
        idx = text_lower.find(keyword)
        if idx != -1:
            window = text_lower[max(0, idx - 120): idx + 120]
            a_in = app_a_lower in window
            b_in = app_b_lower in window
            if a_in and not b_in:
                return app_a_name, text.strip()
            if b_in and not a_in:
                return app_b_name, text.strip()

    # 4. Score-based fallback: count positive-signal proximity
    signals = ["winner", "verdict", "recommend", "superior", "best", "optimal", "definitive", "deploy"]
    score_a = 0
    score_b = 0
    for signal in signals:
        idx = text_lower.find(signal)
        if idx != -1:
            ctx = text_lower[max(0, idx - 100): idx + 100]
            if app_a_lower in ctx:
                score_a += 1
            if app_b_lower in ctx:
                score_b += 1

    if score_a > score_b:
        return app_a_name, text.strip()
    if score_b > score_a:
        return app_b_name, text.strip()

    return "", text.strip()


def _extract_winner_from_html(html_content: str, app_a_name: str, app_b_name: str) -> tuple[str, str]:
    """
    Parse HTML content to extract the winner and verdict reason.
    Looks for .verdict-box, blockquote, <strong>The Verdict</strong>, or conclusion paragraphs.
    Returns: (winner_name, verdict_reason)
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Try .verdict-box (your existing HTML pattern)
    verdict_box = soup.find(class_="verdict-box")
    if verdict_box:
        text = verdict_box.get_text(separator=" ", strip=True)
        winner, reason = _determine_winner_from_text(text, app_a_name, app_b_name)
        if winner:
            return winner, reason

    # 2. Try <blockquote>
    for blockquote in soup.find_all("blockquote"):
        text = blockquote.get_text(separator=" ", strip=True)
        if any(word in text.lower() for word in ["verdict", "winner", "recommend"]):
            winner, reason = _determine_winner_from_text(text, app_a_name, app_b_name)
            if winner:
                return winner, reason

    # 3. Try <strong> or <b> containing "Verdict" / "Winner"
    for elem in soup.find_all(["strong", "b"]):
        label = elem.get_text(strip=True).lower()
        if "verdict" in label or "winner" in label:
            parent = elem.find_parent(["p", "div", "section"])
            if parent:
                full_text = parent.get_text(separator=" ", strip=True)
                winner, reason = _determine_winner_from_text(full_text, app_a_name, app_b_name)
                if winner:
                    return winner, reason

    # 4. Check last few paragraphs for conclusion language
    paragraphs = soup.find_all("p")
    for p in reversed(paragraphs[-5:]):
        text = p.get_text(separator=" ", strip=True)
        if any(word in text.lower() for word in ["winner", "verdict", "recommend", "superior", "choice", "deploy"]):
            winner, reason = _determine_winner_from_text(text, app_a_name, app_b_name)
            if winner:
                return winner, reason

    return "", ""


def _extract_winner_from_body(body: str, app_a_name: str, app_b_name: str) -> tuple[str, str]:
    """
    Extract winner from generated Markdown body text.
    """
    lines = body.split("\n")

    # 1. Explicit markers in the text
    for line in lines:
        line_lower = line.lower()
        if any(marker in line_lower for marker in [
            "winner:", "verdict:", "**the verdict:**", "> **the verdict:**", "> **verdict:**"
        ]):
            return _determine_winner_from_text(line, app_a_name, app_b_name)

    # 2. Markdown blockquotes containing verdict language
    for line in lines:
        if line.startswith(">") and any(word in line.lower() for word in ["verdict", "winner", "recommend", "deploy"]):
            return _determine_winner_from_text(line, app_a_name, app_b_name)

    # 3. Last few non-empty paragraphs
    for line in reversed(lines[-20:]):
        stripped = line.strip()
        if stripped and any(word in stripped.lower() for word in [
            "verdict", "winner", "recommend", "superior", "deploy", "choice", "leads by"
        ]):
            return _determine_winner_from_text(stripped, app_a_name, app_b_name)

    return "", ""


# ============================================================
# 3. Shopify App Store Scraper
# ============================================================
class ShopifyAppScraper:
    def __init__(self):
        self.base_url = "https://apps.shopify.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch_app_metadata(self, app_handle: str) -> dict:
        print(f"Fetching Shopify App Store metadata for [{app_handle}]...")
        url = f"{self.base_url}/{app_handle}"

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            app_name = (
                soup.find("h1").get_text(strip=True)
                if soup.find("h1")
                else app_handle.replace("-", " ").title()
            )

            description_tag = soup.find("div", {"class": "app-details"})
            description = (
                description_tag.get_text(strip=True)[:500]
                if description_tag
                else "Core Shopify infrastructure application."
            )

            return {
                "app_name": app_name,
                "app_handle": app_handle,
                "url": url,
                "description": description,
                "market_position": "Enterprise/Mid-market eCommerce Tool",
            }

        except Exception as e:
            print(f"  Warning: failed to scrape [{app_handle}]. Fallback engaged. Error: {e}")
            return {
                "app_name": app_handle.replace("-", " ").title(),
                "app_handle": app_handle,
                "url": url,
                "description": "Core Shopify infrastructure application.",
            }


# ============================================================
# 4. LLM Engine
# ============================================================
class LLMEngine:
    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name

    def generate_mdx_body(self, app_a: dict, app_b: dict) -> str:
        print(f"Generating technical comparison for [{app_a['app_name']} vs {app_b['app_name']}]...")

        system_prompt = """You are a Senior SaaS Architect and Lead Data Analyst at ToolCompareLabs.
Write a highly technical, data-driven MDX comparison body for Shopify merchants.

CRITICAL CONSTRAINTS:
1. Write entirely in professional US English.
2. FORBIDDEN WORDS: "delve", "game-changer", "skyrocket", "testament", "crucial", "realm", "tapestry".
3. Terminology: use dry engineering terms (latency, DOM bloat, CDN caching, API throughput, JSON payloads, ETL, webhooks).
4. Structure: Executive Summary, Methodology, Core Feature Matrix (Markdown table), Performance Benchmarks, Who Should Choose What.
5. OUTPUT FORMAT: output ONLY clean Markdown/HTML body content. NEVER wrap output in ```markdown or ```html code fences. NEVER add YAML frontmatter. NEVER use inline CSS styles or HTML attributes like border="1".
6. Tables must use plain Markdown table syntax so Tailwind prose styles can target them.
7. CTAs: do NOT include CTA buttons or affiliate links in the body; the frontend injects those automatically."""

        user_prompt = f"""Conduct a deep technical benchmark between these two Shopify apps:

App A:
{json.dumps(app_a, indent=2)}

App B:
{json.dumps(app_b, indent=2)}

Highlight concrete technical differences such as render-blocking scripts, server-side caching strategies, webhook limits, API latency, and payload structure."""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4000,
        )

        raw_output = response.choices[0].message.content
        return self._clean_output(raw_output)

    def suggest_category(self, app_a: dict, app_b: dict) -> str:
        print("Suggesting category for the comparison...")

        prompt = f"""Given these two Shopify apps, return ONLY a short category label (2-4 words) that best describes their shared category.

App A: {app_a['app_name']}
App B: {app_b['app_name']}

Examples: "Marketing Automation", "Page Builder", "CRO", "Search & Discovery", "Loyalty & Retention".
Output only the category label, nothing else."""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50,
        )

        raw = (response.choices[0].message.content or "").strip().strip('"').strip("'")
        # Remove markdown code block wrappers if LLM returns them
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("\n", 1)[0].strip()
        return raw or "Technical Report"

    def summarize_verdict(self, verdict_text: str, winner: str, app_a: dict, app_b: dict) -> str:
        """Use LLM to condense a raw verdict paragraph into a one-sentence verdictReason."""
        prompt = f"""Summarize the following verdict into ONE concise sentence (max 160 characters) explaining why {winner} is the winner.

Verdict text:
{verdict_text}

Output only the sentence, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=120,
            )
            return response.choices[0].message.content.strip().strip('"')
        except Exception:
            return (
                f"{winner} wins in this benchmark due to stronger technical performance, "
                "better scalability, and deeper Shopify integration for enterprise merchants."
            )

    def _clean_output(self, text: str) -> str:
        clean_text = re.sub(r"^```(?:markdown|html)?\s*", "", text, flags=re.MULTILINE)
        clean_text = re.sub(r"^```\s*$", "", clean_text, flags=re.MULTILINE)
        return clean_text.strip()


# ============================================================
# 5. Frontmatter Builder
# ============================================================
def _yaml_str(value: str) -> str:
    """Quote a string if it contains special YAML characters."""
    if value and (":" in value or "#" in value or value.startswith("-") or value.startswith('"')):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def build_frontmatter(
    title: str,
    description: str,
    category: str,
    winner: str,
    verdict_reason: str,
    app_a: dict,
    app_b: dict,
    tags: list[str],
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"title: {_yaml_str(title)}",
        f"description: {_yaml_str(description)}",
        f"pubDate: {today}",
        f"updatedDate: {today}",
        f"category: {_yaml_str(category)}",
        f"winner: {_yaml_str(winner)}",
        f"verdictReason: {_yaml_str(verdict_reason)}",
        "appA:",
        f'  name: {_yaml_str(app_a["app_name"])}',
        f'  link: {_yaml_str(app_a["affiliate_link"])}',
        "appB:",
        f'  name: {_yaml_str(app_b["app_name"])}',
        f'  link: {_yaml_str(app_b["affiliate_link"])}',
        "tags:",
    ]
    for tag in tags:
        lines.append(f'  - {_yaml_str(tag)}')

    return "\n".join(lines)


# ============================================================
# 6. Pipeline
# ============================================================
def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def html_to_markdown_body(html_content: str) -> str:
    """Naive HTML-to-Markdown conversion for existing report HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove style/script tags
    for tag in soup.find_all(["style", "script"]):
        tag.decompose()

    md_lines = []

    for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table", "blockquote", "img"]):
        if elem.name == "h1":
            md_lines.append(f"# {elem.get_text(strip=True)}")
        elif elem.name == "h2":
            md_lines.append(f"\n## {elem.get_text(strip=True)}")
        elif elem.name == "h3":
            md_lines.append(f"\n### {elem.get_text(strip=True)}")
        elif elem.name == "h4":
            md_lines.append(f"\n#### {elem.get_text(strip=True)}")
        elif elem.name == "p":
            text = elem.get_text(separator=" ", strip=True)
            if text:
                md_lines.append(text)
        elif elem.name == "blockquote":
            text = elem.get_text(separator=" ", strip=True)
            md_lines.append(f"> {text}")
        elif elem.name == "table":
            md_lines.append("")
            rows = elem.find_all("tr")
            for i, row in enumerate(rows):
                cells = row.find_all(["th", "td"])
                cell_texts = [c.get_text(strip=True) for c in cells]
                md_lines.append("| " + " | ".join(cell_texts) + " |")
                if i == 0:
                    md_lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
            md_lines.append("")
        elif elem.name == "img":
            src = elem.get("src", "")
            alt = elem.get("alt", "")
            md_lines.append(f"\n![{alt}]({src})\n")

    return "\n".join(md_lines)


def run(
    app_a_handle: str,
    app_b_handle: str,
    affiliate_base_a: str = "",
    affiliate_base_b: str = "",
    html_path: str = "",
):
    # ------------------------------------------------------------------
    # MODE A: Ingest existing HTML report
    # ------------------------------------------------------------------
    if html_path and os.path.exists(html_path):
        print(f"HTML ingestion mode: {html_path}")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")
        title = soup.title.string.strip() if soup.title else f"{app_a_handle} vs {app_b_handle}"

        # Normalize app names from handles if not already known
        app_a_name = app_a_handle.replace("-", " ").title()
        app_b_name = app_b_handle.replace("-", " ").title()

        # Try to infer real app names from the HTML title / h1
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(strip=True)
            # e.g. "PageFly Landing Page Builder vs Shogun ..."
            parts = re.split(r"\s+vs\s+", h1_text, flags=re.IGNORECASE)
            if len(parts) >= 2:
                app_a_name = parts[0].strip()
                app_b_name = parts[1].split(":")[0].strip()

        category_guess = "General"
        meta_tag = soup.find(class_="meta-tag")
        if meta_tag:
            category_guess = meta_tag.get_text(strip=True)

        # Convert body to Markdown
        mdx_body = html_to_markdown_body(html_content)

        # Extract winner + verdict from HTML conclusion
        winner, raw_verdict = _extract_winner_from_html(html_content, app_a_name, app_b_name)
        if not winner:
            winner = app_a_name
            raw_verdict = f"{winner} is the recommended choice based on technical benchmarking."

        # Condense raw verdict into a short verdictReason
        engine = LLMEngine(client, MODEL_NAME)
        verdict_reason = engine.summarize_verdict(raw_verdict, winner, {"app_name": app_a_name}, {"app_name": app_b_name})

        description = (
            f"A data-driven comparison of {app_a_name} and {app_b_name} "
            f"for Shopify merchants. Covers API latency, feature matrix, and engineering trade-offs."
        )
        tags = [
            "shopify",
            category_guess.lower().replace(" ", "-"),
            slugify(app_a_handle),
            slugify(app_b_handle),
        ]

        app_a = {
            "app_name": app_a_name,
            "affiliate_link": affiliate_base_a or f"https://{app_a_handle}.com/?ref=toolcomparelabs",
        }
        app_b = {
            "app_name": app_b_name,
            "affiliate_link": affiliate_base_b or f"https://{app_b_handle}.com/?ref=toolcomparelabs",
        }

        frontmatter = build_frontmatter(
            title=title,
            description=description,
            category=category_guess,
            winner=winner,
            verdict_reason=verdict_reason,
            app_a=app_a,
            app_b=app_b,
            tags=tags,
        )

        output_filename = f"{slugify(app_a_name)}-vs-{slugify(app_b_name)}.md"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        mdx_content = f"---\n{frontmatter}\n---\n\n{mdx_body}\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(mdx_content)

        print(f"\nGenerated MD: {output_path}")
        print(f"Route: /{slugify(app_a_name)}-vs-{slugify(app_b_name)}")
        print(f"Winner detected: {winner}")
        return

    # ------------------------------------------------------------------
    # MODE B: Normal LLM generation pipeline
    # ------------------------------------------------------------------
    scraper = ShopifyAppScraper()
    app_a = scraper.fetch_app_metadata(app_a_handle)
    app_b = scraper.fetch_app_metadata(app_b_handle)

    # Fallback affiliate links if none provided.
    app_a["affiliate_link"] = affiliate_base_a or f"https://{app_a_handle}.com/?ref=toolcomparelabs"
    app_b["affiliate_link"] = affiliate_base_b or f"https://{app_b_handle}.com/?ref=toolcomparelabs"

    engine = LLMEngine(client, MODEL_NAME)
    mdx_body = engine.generate_mdx_body(app_a, app_b)
    category = engine.suggest_category(app_a, app_b)

    # Extract winner from generated body (new smart extraction)
    winner, raw_verdict = _extract_winner_from_body(mdx_body, app_a["app_name"], app_b["app_name"])
    if not winner:
        winner = app_a["app_name"]
        raw_verdict = (
            f"{winner} wins in this benchmark due to stronger technical performance, "
            "better scalability, and deeper Shopify integration for enterprise merchants."
        )

    # Condense into a short verdictReason
    verdict_reason = engine.summarize_verdict(raw_verdict, winner, app_a, app_b)

    title = f"{app_a['app_name']} vs {app_b['app_name']}: Technical Benchmark"
    description = (
        f"A data-driven comparison of {app_a['app_name']} and {app_b['app_name']} "
        f"for Shopify merchants. Covers API latency, feature matrix, and engineering trade-offs."
    )
    tags = [
        tag for tag in [
            "shopify",
            category.lower().replace(" ", "-") if category else "",
            slugify(app_a_handle),
            slugify(app_b_handle),
        ]
        if tag
    ]

    frontmatter = build_frontmatter(
        title=title,
        description=description,
        category=category,
        winner=winner,
        verdict_reason=verdict_reason,
        app_a=app_a,
        app_b=app_b,
        tags=tags,
    )

    output_filename = f"{slugify(app_a['app_name'])}-vs-{slugify(app_b['app_name'])}.md"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    mdx_content = f"---\n{frontmatter}\n---\n\n{mdx_body}\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mdx_content)

    print(f"\nGenerated MD: {output_path}")
    print(f"Route: /{slugify(app_a['app_name'])}-vs-{slugify(app_b['app_name'])}")
    print(f"Winner detected: {winner}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ToolCompareLabs comparison MDX.")
    parser.add_argument("app_a", help="Shopify app handle for competitor A (or app name in HTML mode)")
    parser.add_argument("app_b", help="Shopify app handle for competitor B (or app name in HTML mode)")
    parser.add_argument("--link-a", default="", help="Affiliate link for app A")
    parser.add_argument("--link-b", default="", help="Affiliate link for app B")
    parser.add_argument("--html", default="", help="Path to an existing HTML report to ingest instead of generating")
    args = parser.parse_args()

    run(args.app_a, args.app_b, args.link_a, args.link_b, args.html)
