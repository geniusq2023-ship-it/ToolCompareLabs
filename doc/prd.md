# Product Requirements Document (PRD)
**Project Name:** ToolCompareLabs
**Version:** 1.0
**Target Platform:** Web (Desktop & Mobile Responsive)
**Business Model:** B2B SaaS Affiliate Marketing via pSEO (Programmatic SEO)

## 1. Executive Summary
ToolCompareLabs is a data-driven, highly technical B2B SaaS comparison platform targeting Shopify Plus merchants and enterprise technical directors. Unlike generic review sites, it leverages an automated Python + LLM (DeepSeek) pipeline to generate structural, unbiased, and metric-heavy benchmarks, rendered through a high-performance Astro.js frontend. The goal is to maximize affiliate conversions through "Expert Verdict" UI patterns and Zero-JS loading speeds.

## 2. Target Audience
* **Shopify Merchants (MRR > $50k):** Looking for technical scaling solutions.
* **CTOs / Technical Leads:** Evaluating API latencies, DOM bloat, and webhooks.
* **Affiliate Managers:** Evaluating our site's professionalism to approve high-ticket partnerships.

## 3. Core Features & Requirements

### 3.1 Content Automation Pipeline (Backend)
* **Web Scraper Module:** Scrape raw data, reviews, and metadata from the Shopify App Store.
* **LLM Engine:** Process scraped JSON via DeepSeek API to generate analytical Markdown/MDX content.
* **Strict Formatting:** Output MUST include strict YAML Frontmatter (title, category, affiliate links, tags) and clean HTML/Markdown body without inline CSS.

### 3.2 Frontend Experience (Astro.js)
* **Bottom-Line-Up-Front (BLUF):** Every article must start with an `<ExpertVerdict />` component declaring the winner and immediate CTA buttons.
* **MDX Component System:** Seamlessly render interactive or highly styled components (e.g., `<TechSpecificationTable />`) driven by Frontmatter data.
* **Categorization & Silos:** Auto-generate category index pages (e.g., Marketing Automation, CRO) based on Markdown metadata.
* **Sticky Conversion Elements:** Sidebar or bottom sticky CTA for affiliate links.

## 4. Non-Functional Requirements
* **Performance:** Google Lighthouse scores MUST be 95+ across all metrics. Zero-JS architecture preferred where possible.
* **SEO:** Semantic HTML, auto-generated sitemaps, structured schema data (SoftwareApplication, Article).
* **CI/CD:** Full integration with GitHub and Cloudflare Pages. Merging a `.md` file to `main` must trigger an automatic static build.

## 5. Monetization & Tracking
* Universal support for tracking parameters (Impact.com).
* Global configuration file to manage/update affiliate links to prevent hardcoding deep in components.