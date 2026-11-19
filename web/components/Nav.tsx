"use client";
import { usePathname } from "next/navigation";

const LINKS = [
  ["/", "Overview"],
  ["/results", "Results"],
  ["/queue", "Queue & ideas"],
  ["/guide", "How to read this"],
] as const;

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="Main">
      {LINKS.map(([href, label]) => {
        const active = href === "/" ? path === "/" : path.startsWith(href) || (href === "/results" && path.startsWith("/h/"));
        return (
          <a key={href} href={href} className={active ? "active" : undefined} aria-current={active ? "page" : undefined}>
            {label}
          </a>
        );
      })}
    </nav>
  );
}
