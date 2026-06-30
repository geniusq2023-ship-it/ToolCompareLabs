# ToolCompareLabs 作战计划 —— 三大阶段战术

> **当前状态**：Astro 工业级 pSEO 引擎已就绪，ExpertVerdict / TechMatrix / AffiliateButton 组件就位，Cloudflare Pages CI/CD 通路已打通。
> **当前瓶颈**：仅有 Omnisend 一家大厂 Impact 牌照，急需用内容"钓"出其他品牌审批。

---

## 第一阶段：以战养战，用 Omnisend 钓出其他大厂牌照（本周核心）

### 1.1 灌注第一批内容（立即执行）

目标：72 小时内上线 5 篇 Omnisend 为核心的硬核技术评测。

| # | 文章 | 核心策略 | Winner | 状态 |
|---|---|---|---|---|
| 1 | `omnisend-vs-klaviyo.md` | 放大 Omnisend 在低延迟、快速部署、SMS 路由上的胜势 | **Omnisend** | 已上线，需核查 frontmatter |
| 2 | `omnisend-vs-mailchimp.md` | 打击 Mailchimp 的 Shopify 集成弱、API 限制多、价格陷阱 | **Omnisend** | 待生成 |
| 3 | `omnisend-vs-smsbump.md` | 对比 SMS 专项能力，突出 Omnisend 全渠道统一自动化 | **Omnisend** | 待生成 |
| 4 | `top-3-shopify-marketing-automation-infrastructure-2026.md` | Round-up 评测，Omnisend 排第一，Klaviyo 排第二 | **Omnisend** | 待生成 |
| 5 | `omnisend-vs-activecampaign.md` | 对比 ActiveCampaign 的 CRM 重、Shopify 同步慢 | **Omnisend** | 待生成 |

**执行命令（单篇）**：
```bash
python scripts/saas_matrix_engine.py omnisend mailchimp \
  --link-a "https://your.omnisend.com/VOgZKR" \
  --link-b "https://mailchimp.com/?ref=toolcomparelabs"
```

> 对于 Round-up 类文章（#4），暂时手写 Markdown，frontmatter 中 winner 写 "Omnisend"，并手动插入 TechMatrix 组件。

### 1.2 核查前端组件渲染

- [ ] 每篇文章顶部正确渲染 `<ExpertVerdict />`（Winner 必须是 Omnisend）
- [ ] 绿色 CTA 按钮链接指向 Omnisend Impact 专属链接
- [ ] 表格边框、交替行颜色、深色主题全局一致
- [ ] 移动端底部 StickyCta 正常显示
- [ ] 图片路径 `./xxx.png` 或 `/images/xxx.png` 能正确加载

### 1.3 全站发版

- [ ] 清除 `.astro` 缓存
- [ ] `npm run build` 本地构建通过，无 schema 报错
- [ ] `git add src/content/blog/ src/pages/ src/components/`
- [ ] `git commit -m "feat: launch initial Omnisend-focused comparison batch"`
- [ ] `git push origin main`
- [ ] 确认 Cloudflare Pages 自动编译成功（约 30-60 秒）
- [ ] 线上访问首页，确认 5 篇文章卡片全部出现

### 1.4 扔出诱饵 —— 联盟经理审批战

**时机**：网站上线后，周一上午（联盟经理上班第一时间）。

**操作步骤**：
1. 登录 Impact 后台
2. 找到以下品牌的申请入口：
   - PageFly
   - Shogun
   - Klaviyo
   - Recharge
   - Smile.io
   - Judge.me
3. 在申请理由中粘贴：
   > "ToolCompareLabs is a technical benchmarking studio producing data-driven Shopify app comparisons for enterprise merchants (MRR > $50k). We currently run live benchmarks against your competitors and are looking to add your platform to our 2026 infrastructure matrix. You can review our editorial standards here: https://toolcomparelabs.com"
4. 确保申请时填写的网站 URL 指向已上线的首页

**心理战术**：当联盟经理点开你的站，看到首页全是 Omnisend vs Klaviyo 这种硬核对比，会认为你是一个"有立场、有深度、有流量"的专业评测机构，而不是一个空壳站。审批通过率会大幅上升。

---

## 第二阶段：打通流量闭环，抢占 AI 搜索引用位（下周核心）

### 2.1 结构化数据（Schema.org / JSON-LD）

- [ ] 在 `BaseLayout.astro` 的 `<head>` 中注入 `SoftwareApplication` + `Article` JSON-LD
- [ ] 每篇文章动态渲染 `aggregateRating`、`offers`、`applicationCategory`
- [ ] 确保 DeepSeek 生成的 TechMatrix 数据被包裹在 `<table>` 中（大模型爬虫能直接读取）

### 2.2 自动化社区监控（精准钓鱼）

- [ ] 注册 Reddit API 或配置 n8n Webhook 监控：
  - `r/shopify` 关键词：Klaviyo alternative, Omnisend review, email automation
  - `r/ecommerce` 关键词：shopify plus, marketing automation, SMS marketing
- [ ] 写一个 Python 脚本或 n8n 工作流：
  1. 监控到新帖
  2. 用 DeepSeek API 生成一段 3-4 句的架构师级分析（不提广告）
  3. 末尾自然附带："Our lab ran a full benchmark on these two: [文章链接]"
  4. 自动发布回复

> **红线**：不要硬发广告，不要带 "best" "#1" 等推销话术。要像 StackOverflow 上的技术大牛一样冷酷地丢出数据。

### 2.3 Google Search Console 强推

- [ ] 注册 https://search.google.com/search-console
- [ ] 用 DNS TXT 记录或 HTML 文件验证 `toolcomparelabs.com`
- [ ] 提交 `sitemap-index.xml`
- [ ] 在 GSC 中手动请求收录 5 篇新文章 URL

---

## 第三阶段：系统级升级，让流水线彻底跑通（后续）

### 3.1 联盟链接全局配置

- [ ] 新建 `src/config/affiliateLinks.ts`
- [ ] 集中管理所有品牌链接：
  ```ts
  export const AFFILIATE_LINKS = {
    omnisend: "https://impact.com/xxxx",
    klaviyo:  "https://impact.com/yyyy",
    pagefly:  "https://pagefly.io/?ref=toolcomparelabs",
    shogun:   "https://getshogun.com/?ref=toolcomparelabs",
    // 占位符：审批通过后再替换为 Impact 专属链接
  };
  ```
- [ ] 修改 `ExpertVerdict.astro` 和 `ArticleLayout.astro`，从配置文件读取链接，不再硬编码在 frontmatter 中

### 3.2 自动化流水线打磨

- [ ] 完善 `saas_matrix_engine.py`：
  - [ ] 支持批量生成（读取一个 CSV/JSON 列表，循环输出多篇文章）
  - [ ] 自动抓取 Shopify App Store 评分和评论数，写入 frontmatter
  - [ ] 自动下载 App Store 截图，压缩后存入 `public/images/`
- [ ] 配置 GitHub Actions：每次 `git push` 到 `main` 分支，自动触发 Cloudflare Pages 部署

### 3.3 数据看板

- [ ] 在 Impact 后台每周记录各品牌点击量、转化率、佣金收入
- [ ] 用 Google Analytics 4 或 Plausible（轻量、无 Cookie）追踪文章阅读量
- [ ] 找出 CTR 最高的文章类型，用 DeepSeek 批量复制该类结构

---

## 🏁 本周唯一行动指令

**不要优化样式了。样式永远改不完。**

**现在就执行以下 3 步：**

1. **生成 4 篇新文章**：运行 Python 脚本，把 `omnisend-vs-mailchimp`、`omnisend-vs-smsbump`、`top-3-...`、`omnisend-vs-activecampaign` 推到 `src/content/blog/`
2. **本地验证**：`npm run dev`，确认首页出现 5 篇文章，每篇 Winner 都是 Omnisend
3. **提交代码**：`git add . && git commit -m "feat: initial content batch" && git push`

**周一上午 9:00，打开 Impact，向 PageFly / Shogun / Klaviyo / Recharge 扔出申请。**

内容即武器。开炮。
