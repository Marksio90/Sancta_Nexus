import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/api/",
          "/dashboard",
          "/konto",
          "/admin",
          "/auth/",
        ],
      },
    ],
    sitemap: "https://sanctanexus.pl/sitemap.xml",
    host: "https://sanctanexus.pl",
  };
}
