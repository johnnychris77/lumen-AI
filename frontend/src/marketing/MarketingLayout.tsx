import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Logo } from "./components/Logo";
import { NAV_LINKS } from "./lib/content";
import { track } from "./lib/analytics";

export function MarketingLayout() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  // Close the mobile menu and scroll to top on navigation; emit a page_view.
  useEffect(() => {
    setOpen(false);
    window.scrollTo({ top: 0, behavior: "auto" });
    track("page_view", { path: loc.pathname });
  }, [loc.pathname]);

  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8" aria-label="Primary">
          <Link to="/site" aria-label="LumenAI home">
            <Logo />
          </Link>

          <div className="hidden items-center gap-6 lg:flex">
            {NAV_LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `text-sm font-medium transition-colors hover:text-primary ${
                    isActive ? "text-primary" : "text-slate-600"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
            <Link
              to="/site/contact"
              onClick={() => track("demo_request_click", { placement: "header" })}
              className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-white hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
            >
              Request a demo
            </Link>
          </div>

          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100 lg:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </nav>

        {open && (
          <div id="mobile-menu" className="border-t border-slate-200 bg-white lg:hidden">
            <div className="space-y-1 px-4 py-3">
              {NAV_LINKS.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) =>
                    `block rounded-md px-3 py-2 text-sm font-medium ${
                      isActive ? "bg-primary-subtle text-primary" : "text-slate-700 hover:bg-slate-50"
                    }`
                  }
                >
                  {l.label}
                </NavLink>
              ))}
              <Link to="/site/contact" className="mt-2 block rounded-md bg-primary px-3 py-2 text-center text-sm font-medium text-white">
                Request a demo
              </Link>
            </div>
          </div>
        )}
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-slate-50">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 py-12 sm:px-8 md:grid-cols-[1.5fr_1fr_1fr]">
          <div>
            <Logo />
            <p className="mt-3 max-w-xs text-sm leading-relaxed text-slate-600">
              An AI-powered inspection, evidence, and decision-support platform for medical
              instruments with internal channels and lumens.
            </p>
            <p className="mt-3 text-xs text-slate-400">
              Decision support and evidence governance — not a replacement for trained technicians,
              clinicians, manufacturers, or regulatory authorities.
            </p>
          </div>
          <nav aria-label="Footer — product">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Product</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {NAV_LINKS.slice(0, 5).map((l) => (
                <li key={l.to}>
                  <Link to={l.to} className="text-slate-600 hover:text-primary">{l.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
          <nav aria-label="Footer — engage">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Engage</h2>
            <ul className="mt-3 space-y-2 text-sm">
              <li><Link to="/site/use-cases" className="text-slate-600 hover:text-primary">Use cases</Link></li>
              <li><Link to="/site/video" className="text-slate-600 hover:text-primary">Explainer video</Link></li>
              <li><Link to="/site/contact" className="text-slate-600 hover:text-primary">Request a demonstration</Link></li>
              <li><Link to="/site/contact" className="text-slate-600 hover:text-primary">Discuss a pilot</Link></li>
            </ul>
          </nav>
        </div>
        <div className="border-t border-slate-200">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-5 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8">
            <p>© {new Date().getFullYear()} LumenAI. Demonstration content uses synthetic data — no PHI.</p>
            <p>Designed with healthcare security, traceability, and governance principles in mind.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
