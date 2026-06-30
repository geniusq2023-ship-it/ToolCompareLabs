# Software Design Document (SDD)
**Project Name:** ToolCompareLabs
**Architecture Pattern:** SSG (Static Site Generation) + pSEO Pipeline

## 1. System Architecture
The system is decoupled into a Python-based Content Generator and an Astro-based Static Frontend.

[Content Pipeline (Python)] --> Generates `.mdx` --> [Astro Repository] --> [Cloudflare Pages CI/CD] --> [CDN]

## 2. Tech Stack
* **Content Generation:** Python 3.11+, Requests, BeautifulSoup4, OpenAI SDK (DeepSeek API).
* **Frontend Framework:** Astro.js (v4+)
* **Styling:** Tailwind CSS (for rapid, utility-first UI construction).
* **Hosting/Deployment:** Cloudflare Pages.

## 3. Data Flow & Content Schema
The bridge between the backend pipeline and frontend rendering is the **MDX Frontmatter**.

### Standard Frontmatter Schema (`src/content/blog/schema.ts`)
```typescript
import { z } from 'astro:content';
export const blogSchema = z.object({
  title: z.string(),
  pubDate: z.date(),
  category: z.string(),
  winner: z.string(),
  verdictReason: z.string(),
  appA: z.object({ name: z.string(), link: z.string() }),
  appB: z.object({ name: z.string(), link: z.string() }),
  tags: z.array(z.string()).optional(),
});