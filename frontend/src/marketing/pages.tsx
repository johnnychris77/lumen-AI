import { Link } from "react-router-dom";
import {
  ShieldCheck,
  Eye,
  GitCompareArrows,
  ScrollText,
  Users,
  Layers,
  Lock,
  KeyRound,
  Building2,
  FileCheck2,
  History,
  ArrowRight,
} from "lucide-react";
import { useSeo } from "./lib/seo";
import { Section, SectionHeading, Panel, CtaRow, MaturityBadge, Eyebrow } from "./components/primitives";
import { CAPABILITIES, USE_CASES } from "./lib/content";
import { WorkflowDiagram, WorkflowLegend } from "./components/WorkflowDiagram";
import { EvidencePathDiagram } from "./components/EvidencePathDiagram";
import { WorkflowDemo } from "./components/WorkflowDemo";
import { DashboardPreview } from "./components/DashboardPreview";
import { SpecialistGrid, SpecialistBoundaries } from "./components/SpecialistArchitecture";
import { ContactForm } from "./components/ContactForm";
import { VideoStoryboard } from "./components/VideoStoryboard";
import { DemoDisclaimer } from "./components/DemoDisclaimer";
import { Logo } from "./components/Logo";

/* ─────────────────────────── Home ─────────────────────────── */
export function HomePage() {
  useSeo({
    title: "LumenAI — Inspection evidence & decision support for lumened instruments",
    description:
      "LumenAI turns internal medical-instrument inspection into structured, traceable, reviewable evidence — decision support with human review, not autonomous diagnosis.",
    path: "/site",
  });
  const outcomes = [
    { icon: Eye, title: "See what inspection can't", body: "Bring internal-channel findings into one structured, reviewable record." },
    { icon: GitCompareArrows, title: "Compare against baselines", body: "Review current inspections beside approved baselines for a like-for-like check." },
    { icon: ShieldCheck, title: "Govern the evidence", body: "Hash-chained audit trail, review status, and rationale on every decision." },
    { icon: Users, title: "Keep humans in charge", body: "Uncertain or higher-risk findings route to a qualified reviewer — always." },
  ];
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary-subtle to-white">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 py-16 sm:px-8 sm:py-24 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <Eyebrow>Clinical inspection intelligence</Eyebrow>
            <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl">
              See what traditional inspection cannot.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600">
              LumenAI transforms internal instrument inspection into structured, traceable, and
              reviewable evidence — an AI-assisted decision-support and evidence-governance platform
              for medical instruments with channels and lumens.
            </p>
            <div className="mt-8">
              <CtaRow />
            </div>
            <p className="mt-6 max-w-md text-sm text-slate-500">
              Decision support and evidence governance. Not a replacement for trained technicians,
              clinicians, manufacturers, or regulatory authorities.
            </p>
          </div>
          <div className="lg:justify-self-end">
            <HeroMock />
          </div>
        </div>
      </section>

      {/* Problem teaser */}
      <Section tone="muted">
        <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr] lg:items-center">
          <SectionHeading
            eyebrow="The problem"
            title="Internal channels are the hardest surfaces to inspect — and the hardest to prove."
            intro="Borescope images often live in folders and spreadsheets. Interpretation varies. History is hard to compare. Evidence fragments across systems. Escalation decisions may lack consistent documentation."
          />
          <Panel>
            <ul className="space-y-3 text-sm text-slate-700">
              {[
                "Findings stored as images without structured interpretation.",
                "Inconsistent inspection quality between technicians and shifts.",
                "No easy way to compare an instrument to its own history or an approved baseline.",
                "Audit readiness that depends on reassembling scattered evidence.",
              ].map((t) => (
                <li key={t} className="flex gap-2">
                  <span aria-hidden className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  {t}
                </li>
              ))}
            </ul>
            <Link to="/site/problem" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary-hover">
              Read the full problem <ArrowRight size={14} />
            </Link>
          </Panel>
        </div>
      </Section>

      {/* Outcomes */}
      <Section>
        <SectionHeading eyebrow="Key outcomes" title="From a loose image folder to governed inspection evidence." center />
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {outcomes.map((o) => (
            <div key={o.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <o.icon className="text-primary" size={22} aria-hidden />
              <h3 className="mt-3 text-base font-semibold text-slate-900">{o.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{o.body}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Trust band */}
      <Section tone="brand">
        <div className="grid gap-6 md:grid-cols-[1.3fr_1fr] md:items-center">
          <div>
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Built around governance, not hype.</h2>
            <p className="mt-3 max-w-xl text-base leading-relaxed text-white/85">
              Role-based access, tenant isolation, evidence integrity, and a hash-chained audit trail
              are core to how LumenAI records inspection evidence — designed with healthcare security,
              traceability, and governance principles in mind.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 md:justify-end">
            <Link to="/site/security" className="inline-flex h-11 items-center rounded-md bg-white px-6 text-base font-medium text-primary hover:bg-slate-100">
              Security & governance
            </Link>
            <Link to="/site/workflow" className="inline-flex h-11 items-center rounded-md border border-white/40 px-6 text-base font-medium text-white hover:bg-white/10">
              How it works
            </Link>
          </div>
        </div>
      </Section>
    </>
  );
}

function HeroMock() {
  return (
    <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-4 shadow-lg">
      <div className="mb-3 flex items-center justify-between">
        <Logo />
        <span className="rounded-full bg-primary-subtle px-2 py-0.5 text-[11px] font-semibold text-primary">Inspection</span>
      </div>
      <div className="grid grid-cols-[120px_1fr] gap-3">
        <svg width="120" height="120" viewBox="0 0 150 150" className="rounded-lg" role="img" aria-label="Illustrative borescope view">
          <circle cx="75" cy="75" r="72" fill="#0f172a" />
          <circle cx="75" cy="75" r="58" fill="#1e293b" stroke="#475569" />
          <circle cx="75" cy="75" r="20" fill="#020617" />
          <circle cx="62" cy="70" r="7" fill="#78716c" opacity="0.85" />
          <circle cx="82" cy="86" r="4" fill="#78716c" opacity="0.8" />
        </svg>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between rounded-md bg-slate-50 px-2 py-1.5">
            <span className="text-slate-500">Suggested</span><span className="font-medium text-slate-900">Possible debris</span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-slate-50 px-2 py-1.5">
            <span className="text-slate-500">Baseline</span><span className="font-medium text-warning">deviation</span>
          </div>
          <div className="flex items-center justify-between rounded-md bg-warning-subtle px-2 py-1.5">
            <span className="text-slate-500">Status</span><span className="font-semibold text-warning">Human review</span>
          </div>
        </div>
      </div>
      <DemoDisclaimer className="mt-3" />
    </div>
  );
}

/* ─────────────────────────── Problem ─────────────────────────── */
export function ProblemPage() {
  useSeo({
    title: "The Problem",
    description:
      "Why internal-channel inspection is hard to standardize, compare, and trace — and what stronger inspection evidence would look like.",
    path: "/site/problem",
  });
  const problems = [
    "Internal channels and lumens are difficult to inspect consistently.",
    "Borescope findings are often stored without structured interpretation.",
    "Inspection quality can vary between technicians and shifts.",
    "Historical comparisons across an instrument's life are difficult.",
    "Evidence fragments across imaging tools, spreadsheets, and paper.",
    "Instrument condition trends stay hidden in isolated inspections.",
    "Escalation and review decisions may lack consistent documentation.",
    "Audit readiness depends on reassembling scattered evidence.",
  ];
  return (
    <>
      <Section>
        <SectionHeading
          eyebrow="The problem"
          title="Inspection evidence is hard to standardize, compare, review, and trace."
          intro="These are structural challenges in how internal-channel inspection evidence is captured and used today. LumenAI is built to address the evidence and workflow layer — responsibly, and without overstating outcomes."
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {problems.map((p, i) => (
            <div key={p} className="flex gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <span aria-hidden className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500">{i + 1}</span>
              <p className="text-sm leading-relaxed text-slate-700">{p}</p>
            </div>
          ))}
        </div>
      </Section>
      <Section tone="muted">
        <Panel className="mx-auto max-w-3xl">
          <h3 className="text-lg font-semibold text-slate-900">A responsible framing</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            LumenAI does not claim to reduce infection rates, guarantee regulatory compliance, or
            replace clinical judgment. It aims to help teams move from subjective visual inspection
            toward a more standardized, traceable, evidence-based process — with a qualified human
            owning every decision.
          </p>
        </Panel>
      </Section>
    </>
  );
}

/* ─────────────────────────── Workflow ─────────────────────────── */
export function WorkflowPage() {
  useSeo({
    title: "How LumenAI Works",
    description:
      "A ten-step inspection workflow: identify, capture, validate, analyze, compare with baseline, rank, route for human review, record evidence, and report.",
    path: "/site/workflow",
  });
  return (
    <>
      <Section>
        <SectionHeading
          eyebrow="How it works"
          title="Ten steps from instrument to governed evidence."
          intro="Automated analysis, human review, baseline comparison, evidence governance, and reporting are distinct, labeled stages — never blurred together."
        />
        <div className="mb-6"><WorkflowLegend /></div>
        <WorkflowDiagram />
      </Section>

      <Section tone="muted" id="demo">
        <SectionHeading
          eyebrow="Interactive demo"
          title="Walk the workflow with synthetic data."
          intro="Select a demo instrument and sample image, run the assistive analysis, compare against a baseline, see review routing, and generate a sample report. Nothing here touches production data."
        />
        <WorkflowDemo />
      </Section>

      <Section>
        <SectionHeading eyebrow="Evidence path" title="How a finding becomes traceable evidence." />
        <EvidencePathDiagram />
        <p className="mt-4 max-w-2xl text-sm text-slate-600">
          Each stage adds to the record rather than overwriting it: capture and metadata create the
          evidence, analysis and baseline comparison inform it, human review decides it, and the
          audit trail preserves it for reporting.
        </p>
      </Section>
    </>
  );
}

/* ─────────────────────────── Platform ─────────────────────────── */
export function PlatformPage() {
  useSeo({
    title: "Platform Capabilities",
    description:
      "LumenAI platform capabilities — borescope review, structured records, baseline comparison, evidence integrity, review routing, audit logging, RBAC, and reporting.",
    path: "/site/platform",
  });
  return (
    <>
      <Section>
        <SectionHeading
          eyebrow="Platform"
          title="Capabilities, labeled honestly."
          intro="Each capability is tagged by maturity so you always know what is in the product today, what is demonstrated with simulated data, and what is concept stage."
        />
        <div className="mb-6 flex flex-wrap gap-2 text-xs">
          <span className="inline-flex items-center gap-1 rounded-full bg-success-subtle px-2.5 py-0.5 font-semibold text-success">In product</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-info-subtle px-2.5 py-0.5 font-semibold text-info">Demonstrated with simulated data</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-warning-subtle px-2.5 py-0.5 font-semibold text-warning">Concept stage</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h3 className="text-base font-semibold text-slate-900">{c.title}</h3>
              </div>
              <p className="flex-1 text-sm leading-relaxed text-slate-600">{c.body}</p>
              <div className="mt-3"><MaturityBadge maturity={c.maturity} /></div>
            </div>
          ))}
        </div>
      </Section>

      <Section tone="muted">
        <SectionHeading eyebrow="Dashboard preview" title="Operational visibility, at a glance." intro="A concept dashboard built from synthetic data to illustrate the shape of insight — inspection volume, review-required cases, finding categories, and trends." />
        <DashboardPreview />
      </Section>

      <Section>
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-slate-900">More than borescope image storage</h3>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">A basic image app</p>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
                <li>Stores images in folders</li>
                <li>Leaves interpretation entirely manual</li>
                <li>No baseline lineage or history</li>
                <li>No structured review or audit trail</li>
              </ul>
            </div>
            <div className="rounded-lg bg-primary-subtle p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-primary">LumenAI</p>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                <li>Structured inspection records with metadata</li>
                <li>Assistive analysis with human confirmation</li>
                <li>Baseline-aware comparison and instrument history</li>
                <li>Review routing, rationale, and a hash-chained audit trail</li>
              </ul>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}

/* ─────────────────────────── Architecture ─────────────────────────── */
export function ArchitecturePage() {
  useSeo({
    title: "AI Specialist Architecture",
    description:
      "How LumenAI's AI specialists contribute analysis and decision support within strict boundaries — each with defined inputs, outputs, and what it may and may not do.",
    path: "/site/architecture",
  });
  return (
    <>
      <Section>
        <SectionHeading
          eyebrow="AI architecture"
          title="Specialists that assist — never decide alone."
          intro="LumenAI composes focused specialists, each with a narrow purpose. Descriptions here follow the platform's own specialist catalog, including where a name is infrastructure or a sub-capability rather than a standalone agent."
        />
        <div className="mb-8"><SpecialistBoundaries /></div>
        <SpecialistGrid />
      </Section>
      <Section tone="muted">
        <Panel className="mx-auto max-w-3xl">
          <h3 className="text-lg font-semibold text-slate-900">Honest about the model</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">
            The image-analysis layer in the current build runs a documented placeholder scorer rather
            than a trained, validated computer-vision model. It is presented as assistive only, and a
            trained model requires formal validation before any finding could be treated as more than
            a suggestion. We would rather tell you this than imply otherwise.
          </p>
        </Panel>
      </Section>
    </>
  );
}

/* ─────────────────────────── Security ─────────────────────────── */
export function SecurityPage() {
  useSeo({
    title: "Security & Governance",
    description:
      "How LumenAI approaches authentication, authorization, tenant isolation, evidence integrity, audit logging, and human oversight — designed with healthcare governance principles.",
    path: "/site/security",
  });
  const controls = [
    { icon: KeyRound, title: "Authentication", body: "Token-based authentication gates access to the platform." },
    { icon: Users, title: "Role-based access", body: "Permissions are scoped by role so users see only what their role allows." },
    { icon: Building2, title: "Tenant isolation", body: "Data is scoped per tenant and enforced at the API layer — tenants never see each other's raw data." },
    { icon: ShieldCheck, title: "Evidence integrity", body: "Inspection evidence and decisions are recorded to a hash-chained, tamper-evident audit trail." },
    { icon: ScrollText, title: "Audit logging", body: "User actions, review decisions, and evidence events are appended to an immutable log." },
    { icon: Lock, title: "Least-privilege architecture", body: "Sensitive operations are restricted and separated by role and scope." },
    { icon: History, title: "Versioned APIs", body: "APIs are versioned to keep integrations stable as the platform evolves." },
    { icon: FileCheck2, title: "Human oversight", body: "Higher-risk and uncertain findings route to a qualified human reviewer by design." },
  ];
  return (
    <>
      <Section>
        <SectionHeading
          eyebrow="Security & governance"
          title="Designed with healthcare security, traceability, and governance principles in mind."
          intro="The controls below describe how the platform is built. They are engineering and governance controls — not regulatory certifications."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {controls.map((c) => (
            <div key={c.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <c.icon className="text-primary" size={20} aria-hidden />
              <h3 className="mt-3 text-sm font-semibold text-slate-900">{c.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-600">{c.body}</p>
            </div>
          ))}
        </div>
      </Section>
      <Section tone="muted">
        <Panel className="mx-auto max-w-3xl border-warning/30 bg-warning-subtle">
          <h3 className="text-lg font-semibold text-slate-900">What we do not claim</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">
            LumenAI does not claim HIPAA compliance, FDA clearance, SOC 2 certification, or any
            cybersecurity or regulatory certification. Statements here describe design intent and
            implemented controls, not third-party attestations. Any compliance posture is established
            with your organization and the appropriate authorities.
          </p>
        </Panel>
      </Section>
    </>
  );
}

/* ─────────────────────────── Use cases ─────────────────────────── */
export function UseCasesPage() {
  useSeo({
    title: "Use Cases",
    description:
      "How sterile processing, infection prevention, quality, risk, and executive teams can use LumenAI — from routine inspection to audit preparation and multi-site trend review.",
    path: "/site/use-cases",
  });
  return (
    <Section>
      <SectionHeading eyebrow="Use cases" title="Where LumenAI fits into real workflows." intro="Illustrative scenarios across roles. Examples avoid patient-specific or regulatory guarantees." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {USE_CASES.map((u) => (
          <div key={u.title} className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <span className="inline-flex w-fit items-center rounded-full bg-primary-subtle px-2.5 py-0.5 text-[11px] font-semibold text-primary">{u.audience}</span>
            <h3 className="mt-3 text-base font-semibold text-slate-900">{u.title}</h3>
            <p className="mt-1 flex-1 text-sm leading-relaxed text-slate-600">{u.body}</p>
          </div>
        ))}
      </div>
      <div className="mt-10"><CtaRow align="start" /></div>
    </Section>
  );
}

/* ─────────────────────────── Video ─────────────────────────── */
export function VideoPage() {
  useSeo({
    title: "Explainer Video",
    description:
      "A 90-second explainer concept for LumenAI — storyboard-based interactive preview, plus the full narration script, scene-by-scene storyboard, and captions.",
    path: "/site/video",
  });
  return (
    <>
      <Section>
        <SectionHeading
          eyebrow="Explainer video"
          title="Better visibility. Better evidence. Better decisions."
          intro="A storyboard-based preview stands in for the finished ~110-second explainer. Step through each scene to see the on-screen text, narration, animation direction, and timing. The full script, storyboard, and captions ship in the repository."
        />
        <VideoStoryboard />
        <div className="mt-6 grid gap-3 sm:grid-cols-3 text-sm">
          <Panel><h3 className="font-semibold text-slate-900">Script & storyboard</h3><p className="mt-1 text-slate-600">docs/marketing/VIDEO_SCRIPT.md and VIDEO_STORYBOARD.md.</p></Panel>
          <Panel><h3 className="font-semibold text-slate-900">Captions</h3><p className="mt-1 text-slate-600">WebVTT caption file at public/site/lumenai-explainer.vtt.</p></Panel>
          <Panel><h3 className="font-semibold text-slate-900">Production</h3><p className="mt-1 text-slate-600">Build notes (Remotion / screen capture / FFmpeg) in the storyboard doc.</p></Panel>
        </div>
      </Section>
    </>
  );
}

/* ─────────────────────────── About ─────────────────────────── */
export function AboutPage() {
  useSeo({
    title: "About the Product",
    description:
      "The vision behind LumenAI — improving visibility into difficult-to-inspect instruments and turning isolated inspection findings into usable operational intelligence.",
    path: "/site/about",
  });
  const pillars = [
    "Improving visibility into difficult-to-inspect instruments.",
    "Supporting sterile processing quality and consistency.",
    "Standardizing how inspection evidence is captured and described.",
    "Strengthening interdisciplinary review across SPD, IP, and quality.",
    "Turning isolated inspection findings into usable operational intelligence.",
  ];
  return (
    <>
      <Section>
        <SectionHeading eyebrow="About" title="Turning inspection into evidence — and evidence into intelligence." intro="LumenAI exists to help teams inspect what is hardest to see and to make the resulting evidence structured, comparable, and reviewable." />
        <ul className="grid gap-3 sm:grid-cols-2">
          {pillars.map((p) => (
            <li key={p} className="flex gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <Layers className="mt-0.5 shrink-0 text-primary" size={18} aria-hidden />
              <span className="text-sm leading-relaxed text-slate-700">{p}</span>
            </li>
          ))}
        </ul>
      </Section>
      <Section tone="brand">
        <div className="text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">Let&apos;s talk about a pilot.</h2>
          <p className="mx-auto mt-3 max-w-xl text-white/85">See the workflow, discuss a pilot, or join the product-validation program.</p>
          <Link to="/site/contact" className="mt-6 inline-flex h-11 items-center rounded-md bg-white px-6 text-base font-medium text-primary hover:bg-slate-100">
            Contact the LumenAI team
          </Link>
        </div>
      </Section>
    </>
  );
}

/* ─────────────────────────── Contact ─────────────────────────── */
export function ContactPage() {
  useSeo({
    title: "Request a Demonstration",
    description:
      "Request a LumenAI demonstration, discuss a pilot, or join the product-validation program. Configurable, secure contact form — no PHI.",
    path: "/site/contact",
  });
  return (
    <Section>
      <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <SectionHeading
            eyebrow="Get in touch"
            title="Request a demonstration or discuss a pilot."
            intro="Tell us a little about your organization and what you're interested in. We'll follow up to schedule time."
          />
          <ul className="space-y-3 text-sm text-slate-700">
            {["Request a demonstration", "Explore the workflow", "Discuss a pilot", "Join the product-validation program"].map((t) => (
              <li key={t} className="flex items-center gap-2"><ArrowRight size={14} className="text-primary" aria-hidden /> {t}</li>
            ))}
          </ul>
          <p className="mt-6 text-xs text-slate-500">
            Please do not include protected health information in this form. Submissions run in
            demonstration mode unless a secure endpoint is configured by the host.
          </p>
        </div>
        <Panel>
          <ContactForm />
        </Panel>
      </div>
    </Section>
  );
}

/* ─────────────────────────── 404 ─────────────────────────── */
export function NotFoundPage() {
  useSeo({ title: "Page not found", description: "The page you requested does not exist.", path: "/site" });
  return (
    <Section>
      <div className="mx-auto max-w-lg text-center">
        <p className="text-5xl font-extrabold text-primary">404</p>
        <h1 className="mt-3 text-xl font-semibold text-slate-900">We couldn&apos;t find that page.</h1>
        <Link to="/site" className="mt-6 inline-flex h-11 items-center rounded-md bg-primary px-6 text-base font-medium text-white hover:bg-primary-hover">
          Back to home
        </Link>
      </div>
    </Section>
  );
}
