import type { MetadataRoute } from "next";

import { listBooks } from "@/lib/api";
import { bookPath } from "@/lib/format";
import { siteUrl } from "@/lib/seo";

/**
 * Built on request, not at build time: the build has no API to ask. The API
 * answers come from the fetch cache (a few minutes), so this stays cheap.
 */
export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = siteUrl();
  const books = await listBooks();
  return [
    { url: `${base}/`, changeFrequency: "daily", priority: 1 },
    ...books.map((book) => ({
      url: `${base}${bookPath(book.isbn13, book.title)}`,
      changeFrequency: "daily" as const,
      priority: 0.8,
    })),
  ];
}
