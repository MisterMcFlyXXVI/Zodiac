import type { MetadataRoute } from "next";

// Lets the dashboard be added to a phone's Home Screen as an app.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "zbot · Zodiac Z13 & Z32",
    short_name: "zbot",
    description: "Results of an automated, statistically honest search of the unsolved Zodiac ciphers.",
    start_url: "/",
    display: "standalone",
    background_color: "#121211",
    theme_color: "#121211",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
