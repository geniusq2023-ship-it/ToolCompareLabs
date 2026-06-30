import { z } from 'astro:content';

export const blogSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  pubDate: z.coerce.date(),
  updatedDate: z.coerce.date().optional(),
  category: z.string(),
  winner: z.string(),
  verdictReason: z.string(),
  appA: z.object({ name: z.string(), link: z.string() }),
  appB: z.object({ name: z.string(), link: z.string() }),
  tags: z.array(z.string()).optional(),
});

export type BlogSchema = z.infer<typeof blogSchema>;
