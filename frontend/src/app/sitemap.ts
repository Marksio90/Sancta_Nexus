import type { MetadataRoute } from "next";

const BASE_URL = "https://sanctanexus.pl";

const NOVENA_IDS = [
  "milosierdzie",
  "duch_swiety",
  "matka_boza",
  "sw_jozef",
  "sw_michal",
  "eucharystia",
  "sw_faustyna",
  "sw_jan_pawel",
];

const STATIC_ROUTES: Array<{
  path: string;
  priority: number;
  changeFrequency: MetadataRoute.Sitemap[0]["changeFrequency"];
}> = [
  { path: "/", priority: 1.0, changeFrequency: "daily" },
  { path: "/lectio-divina", priority: 0.9, changeFrequency: "weekly" },
  { path: "/asystent-refleksji", priority: 0.9, changeFrequency: "weekly" },
  { path: "/breviary", priority: 0.8, changeFrequency: "daily" },
  { path: "/dzisiaj", priority: 0.8, changeFrequency: "daily" },
  { path: "/bible", priority: 0.8, changeFrequency: "monthly" },
  { path: "/rozaniec", priority: 0.8, changeFrequency: "weekly" },
  { path: "/nowenna", priority: 0.7, changeFrequency: "monthly" },
  { path: "/rachunek-sumienia", priority: 0.7, changeFrequency: "monthly" },
  { path: "/intencje", priority: 0.6, changeFrequency: "weekly" },
  { path: "/grupy", priority: 0.6, changeFrequency: "weekly" },
  { path: "/cennik", priority: 0.5, changeFrequency: "monthly" },
  { path: "/guest", priority: 0.8, changeFrequency: "monthly" },
  { path: "/regulamin", priority: 0.3, changeFrequency: "yearly" },
  { path: "/polityka-prywatnosci", priority: 0.3, changeFrequency: "yearly" },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  const staticEntries: MetadataRoute.Sitemap = STATIC_ROUTES.map((r) => ({
    url: `${BASE_URL}${r.path}`,
    lastModified: now,
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));

  const novenaEntries: MetadataRoute.Sitemap = NOVENA_IDS.map((id) => ({
    url: `${BASE_URL}/nowenna/${id}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: 0.8,
  }));

  // English landing page
  const englishEntries: MetadataRoute.Sitemap = [
    {
      url: `${BASE_URL}/en`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.9,
    },
    {
      url: `${BASE_URL}/en/guest`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    },
  ];

  return [...staticEntries, ...novenaEntries, ...englishEntries];
}
