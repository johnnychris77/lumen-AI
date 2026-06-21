# Localization Strategy — LumenAI International

**Document ID:** LUM-GLOBAL-004  
**Version:** 1.0  
**Status:** Planning  
**Milestone:** P20 — International Expansion & Global Regulatory Readiness  
**Classification:** Product Confidential  

---

## 1. Overview

This document defines LumenAI's internationalization (i18n) and localization (l10n) strategy for the React-based frontend and associated backend services. As LumenAI expands into international markets, the platform must support multiple languages, regional date/time and currency formats, locale-specific SPD terminology, and right-to-left (RTL) language layouts.

Localization is approached in two layers:
1. **i18n Foundation** — technical framework supporting multiple languages without code changes
2. **l10n Content** — locale-specific translations, terminology, and formatting

---

## 2. i18n Framework — react-i18next

### 2.1 Framework Selection

**Recommended Framework:** `react-i18next` (backed by `i18next`)

**Rationale:**
- Industry-standard React i18n framework with active maintenance
- Supports namespace-based translation organization (separate namespaces for UI, medical terminology, regulatory)
- Pluralization support for all target languages
- Interpolation, formatting, and date/number localization via `i18next-icu` or `react-intl` integration
- SSR (server-side rendering) compatible
- Lazy loading of translation bundles (performance optimization for large translation files)
- TypeScript support for type-safe translation keys

**Core Packages:**
```json
{
  "i18next": "^23.x",
  "react-i18next": "^14.x",
  "i18next-http-backend": "^2.x",
  "i18next-browser-languagedetector": "^7.x",
  "i18next-icu": "^2.x"
}
```

### 2.2 Architecture

```
frontend/src/
├── i18n/
│   ├── index.ts              # i18next initialization
│   ├── config.ts             # Language configuration, fallbacks
│   └── locales/
│       ├── en/               # English (default)
│       │   ├── common.json   # General UI strings
│       │   ├── spd.json      # SPD terminology
│       │   ├── regulatory.json # Regulatory terminology
│       │   └── errors.json   # Error messages
│       ├── fr/               # French (Canada/EU)
│       │   ├── common.json
│       │   ├── spd.json
│       │   ├── regulatory.json
│       │   └── errors.json
│       ├── de/               # German (EU)
│       ├── ja/               # Japanese
│       ├── ko/               # Korean
│       ├── es/               # Spanish (LatAm)
│       └── ar/               # Arabic (future — UAE/Saudi)
```

### 2.3 i18next Configuration

```typescript
// frontend/src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: ['en', 'fr', 'de', 'ja', 'ko', 'es', 'ar'],
    ns: ['common', 'spd', 'regulatory', 'errors'],
    defaultNS: 'common',
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    detection: {
      order: ['querystring', 'cookie', 'localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage', 'cookie'],
    },
    interpolation: {
      escapeValue: false, // React handles XSS
    },
    returnNull: false,
    returnEmptyString: false,
  });

export default i18n;
```

### 2.4 Translation Key Conventions

```typescript
// Namespace-qualified keys
t('spd:instrument.inspection.result')     // SPD domain
t('regulatory:classification.class_ii')   // Regulatory domain
t('common:button.submit')                 // Generic UI

// Parameterized translations
t('spd:instrument.count', { count: 42 })  // Pluralization
t('common:greeting', { name: userName })  // Interpolation
```

---

## 3. Language Support Roadmap

### 3.1 Language Priority Matrix

| Language | Code | Markets | Phase | Target Quarter |
|----------|------|---------|-------|----------------|
| English | en | US, Canada, UK, Australia, Singapore, NZ | CURRENT | Live |
| French (Canadian) | fr-CA | Canada (Quebec) | Phase 1 | Q2 Year 1 |
| French (European) | fr-FR | EU (France, Belgium, Luxembourg) | Phase 2 | Q1 Year 2 |
| German | de-DE | EU (Germany, Austria, Switzerland) | Phase 2 | Q1 Year 2 |
| Spanish (LatAm) | es-419 | Latin America expansion | Phase 3 | Q3 Year 2 |
| Japanese | ja-JP | Japan | Phase 4 | Year 3 |
| Korean | ko-KR | South Korea | Phase 3 | Q4 Year 2 |
| Arabic | ar | UAE, Saudi Arabia | Phase 5 | Year 3+ |

### 3.2 Phase 1 — French Canadian (Q2 Year 1)

**Scope:** Full UI translation for Quebec market entry  
**Priority strings:** All SPD workflow screens, inspection results, quality dashboards, error messages, regulatory terminology in Quebec French (OQLF compliance)  
**Translation approach:** Professional translation by certified medical translator; review by OQLF-compliant bilingual SPD professional  
**Special considerations:**
- Quebec French differs from European French in terminology and register
- OQLF (Office québécois de la langue française) — must use approved French terminology for software in Quebec
- Medical terminology: "instruments chirurgicaux" (surgical instruments), "décontamination" (decontamination), "retraitement" (reprocessing)

### 3.3 Phase 2 — German and French EU (Q1 Year 2)

**German (de-DE):**
- DGSV terminology alignment (Aufbereitung, Sterilgutversorgung, Sterilisation, Desinfektion)
- Formal register ("Sie" form for professional settings)
- Compound word handling — German frequently creates long compound words; UI design must accommodate
- Gender-sensitive language considerations

**French European (fr-FR):**
- Differs from fr-CA in some terminology
- French SPD terminology: "stérilisation centrale" (central sterilization), "désinfection de haut niveau" (high-level disinfection)

### 3.4 Phase 3 — Spanish and Korean (Q3–Q4 Year 2)

**Spanish LatAm (es-419):**
- Neutral LatAm Spanish (avoids country-specific regionalisms)
- Medical terminology: Spanish-language CRCST materials as reference
- Preparation for LatAm market expansion (Brazil excluded — Portuguese)

**Korean (ko-KR):**
- Formal register required for healthcare professional context
- Korean SPD terminology aligned with MFDS and KSSS guidance
- Honorific system — "합쇼체" (hapjoche) formal level required

### 3.5 Phase 4 — Japanese (Year 3)

**Japanese (ja-JP):**
- Three writing systems: Hiragana, Katakana, Kanji — all required in UI
- Professional medical Japanese — keigo (敬語 — formal/honorific register)
- PMDA and JSSP terminology alignment
- Character width: Full-width vs half-width characters; UI layout impact
- Vertical text option: Not required for initial release; horizontal layout acceptable for professional clinical UI

### 3.6 Phase 5 — Arabic (Year 3+)

**Arabic (ar):**
- RTL (right-to-left) layout — requires full UI RTL refactoring (see Section 7)
- Modern Standard Arabic (MSA) for UI; Gulf dialect considerations for UAE/Saudi
- Medical Arabic terminology: SFDA and MOH terminology reference
- Numeral systems: Eastern Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩) in some regional contexts; Western Arabic numerals standard in medical/professional contexts

---

## 4. Date/Time Localization

### 4.1 Internal Storage Standard

- **All dates/times stored in UTC** in database and API payloads
- ISO 8601 format for all API responses: `2026-06-21T14:30:00Z`
- No localized dates in API layer; localization performed at frontend display layer

### 4.2 Display Format by Locale

| Locale | Date Format | Time Format | Example Date | Example Time |
|--------|-------------|-------------|--------------|--------------|
| en-US | MM/DD/YYYY | 12-hour (h:mm a) | 06/21/2026 | 2:30 PM |
| en-CA | DD/MM/YYYY or YYYY-MM-DD | 12/24-hour | 21/06/2026 | 14:30 |
| en-GB | DD/MM/YYYY | 24-hour | 21/06/2026 | 14:30 |
| en-AU | DD/MM/YYYY | 12-hour | 21/06/2026 | 2:30 PM |
| fr-CA | YYYY-MM-DD (ISO standard) | 24-hour | 2026-06-21 | 14 h 30 |
| fr-FR | DD/MM/YYYY | 24-hour | 21/06/2026 | 14:30 |
| de-DE | DD.MM.YYYY | 24-hour | 21.06.2026 | 14:30 Uhr |
| ja-JP | YYYY年MM月DD日 | 24-hour | 2026年06月21日 | 14:30 |
| ko-KR | YYYY년 MM월 DD일 | 24-hour | 2026년 06월 21일 | 14:30 |
| ar | DD/MM/YYYY | 12-hour (am/pm) | ٢١/٠٦/٢٠٢٦ | ٢:٣٠ م |

### 4.3 Implementation

```typescript
// Use Intl.DateTimeFormat for locale-aware formatting
const formatDate = (date: Date, locale: string): string => {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
};

const formatDateTime = (date: Date, locale: string, timeZone: string): string => {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(date);
};
```

### 4.4 Time Zone Handling

- All timestamps stored in UTC
- User time zone stored in user profile preferences (`timezone` field, IANA tz database format, e.g., `America/Toronto`, `Europe/London`)
- Display conversion performed in frontend using `Intl.DateTimeFormat` with user's time zone
- Inspection timestamps displayed in local hospital time zone (critical for audit trail interpretation)

---

## 5. Currency Localization

### 5.1 Supported Currencies

| Currency | Code | Symbol | Markets | Formatting Example |
|----------|------|--------|---------|-------------------|
| US Dollar | USD | $ | United States | $1,234.56 |
| Canadian Dollar | CAD | CA$ | Canada | CA$1,234.56 |
| British Pound | GBP | £ | United Kingdom | £1,234.56 |
| Euro | EUR | € | EU | €1.234,56 (de) / 1 234,56 € (fr) |
| Australian Dollar | AUD | A$ | Australia | A$1,234.56 |
| Singapore Dollar | SGD | S$ | Singapore | S$1,234.56 |
| Japanese Yen | JPY | ¥ | Japan | ¥123,456 (no decimal) |
| South Korean Won | KRW | ₩ | South Korea | ₩1,234,567 (no decimal) |
| UAE Dirham | AED | AED | UAE | AED 1,234.56 |
| Saudi Riyal | SAR | SAR | Saudi Arabia | SAR 1,234.56 |

### 5.2 Currency Implementation

```typescript
const formatCurrency = (amount: number, currency: string, locale: string): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: currency === 'JPY' || currency === 'KRW' ? 0 : 2,
  }).format(amount);
};
```

### 5.3 Billing Architecture

- Invoicing currency: Customer's local currency (configurable per tenant)
- Base pricing in USD; local currency conversion at billing via Stripe international pricing
- Currency display in UI: Read-only display of subscription/invoice amounts
- FX risk: Managed via quarterly pricing reviews; not real-time conversion

---

## 6. Measurement Localization

### 6.1 Measurement Standards

| Measurement | LumenAI Standard | Regional Note |
|-------------|-----------------|---------------|
| Length (instrument dimensions) | Millimeters (mm) | Metric standard globally |
| Weight | Grams (g), Kilograms (kg) | Metric standard globally |
| Temperature (sterilization cycles) | Celsius (°C) | Global standard for medical use |
| Pressure (autoclave) | kPa or bar | SI units standard |
| US Customary fallback | inches, °F | US legacy display option only |

### 6.2 Implementation

- Default: Metric (SI) for all regions including US professional medical context
- US legacy option: Configurable per user preference to display US customary equivalents (not primary)
- Sterilization temperature: Always displayed in °C with °F in parentheses for US locale: `134°C (273°F)`
- Dimensions: mm standard; US locale may show mm with inches in parentheses

```typescript
// Measurement conversion utilities
const mmToInches = (mm: number): number => mm / 25.4;
const celsiusToFahrenheit = (c: number): number => (c * 9/5) + 32;

const formatTemperature = (celsius: number, locale: string): string => {
  if (locale.startsWith('en-US')) {
    return `${celsius}°C (${Math.round(celsiusToFahrenheit(celsius))}°F)`;
  }
  return `${celsius}°C`;
};
```

---

## 7. SPD Terminology Localization

### 7.1 Core SPD Terminology — Regional Differences

| Concept | US (en-US) | UK (en-GB) | Canada (en-CA) | Australia (en-AU) |
|---------|------------|------------|----------------|-------------------|
| Operating Room | OR | Theatre / Operating Theatre | OR or Theatre | Theatre |
| Sterile Processing Department | SPD | HSDU (Hospital Sterilisation and Disinfection Unit) / SSD | SPD or CSPD | CSSD (Central Sterile Services Department) |
| Decontamination | Decontamination | Decontamination | Decontamination | Decontamination / Reprocessing |
| Sterilization | Sterilization | Sterilisation | Sterilization | Sterilisation |
| Instrument | Instrument | Instrument | Instrument | Instrument |
| Tray | Tray or Set | Tray or Pack | Tray or Set | Tray or Set |
| Washer-Disinfector | Washer-Disinfector | Washer-Disinfector | Washer-Disinfector | Washer-Disinfector |
| Reprocessing | Reprocessing | Reprocessing | Reprocessing | Reprocessing |
| Sterile barrier system | Sterile barrier system | Sterile barrier | Sterile barrier system | Sterile barrier system |
| Count sheet / Preference card | Count sheet / Preference card | Instrument checklist | Count sheet | Count sheet |
| Inspection | Inspection | Inspection | Inspection | Inspection |
| Loaner instruments | Loaner instruments | Loan instruments | Loaner instruments | Loan instruments / Loaner sets |

### 7.2 SPD Terminology Namespace (en-GB example)

```json
// locales/en-GB/spd.json
{
  "department": {
    "name": "HSDU / Sterile Services Department",
    "abbrev": "HSDU"
  },
  "or": {
    "name": "Operating Theatre",
    "abbrev": "Theatre"
  },
  "sterilization": "Sterilisation",
  "reprocessing": "Decontamination and Sterilisation",
  "instrument_tray": "Instrument Tray",
  "loaner": "Loan Instruments"
}
```

### 7.3 German SPD Terminology

```json
// locales/de-DE/spd.json
{
  "department": {
    "name": "Zentrale Sterilgutversorgungsabteilung",
    "abbrev": "ZSVA"
  },
  "sterilization": "Sterilisation",
  "reprocessing": "Aufbereitung",
  "decontamination": "Desinfektion",
  "inspection": "Sichtprüfung",
  "instrument": "Medizinprodukt / Instrument",
  "sterile_barrier": "Sterilbarrieresystem",
  "washer_disinfector": "Reinigungs- und Desinfektionsgerät (RDG)"
}
```

### 7.4 Japanese SPD Terminology

```json
// locales/ja-JP/spd.json
{
  "department": {
    "name": "中央材料室",
    "abbrev": "中材"
  },
  "sterilization": "滅菌",
  "reprocessing": "再製",
  "decontamination": "汚染除去",
  "inspection": "目視検査",
  "instrument": "手術器械",
  "sterile_barrier": "滅菌バリアシステム"
}
```

---

## 8. Regulatory Terminology Localization

### 8.1 Regulatory Framework Terminology by Region

| Concept | US/FDA | EU MDR | UK MHRA | TGA Australia | HSA Singapore | PMDA Japan |
|---------|--------|--------|---------|---------------|---------------|------------|
| Device authorization | 510(k) Clearance | CE Marking | UKCA Registration | ARTG Inclusion | Product Registration | Marketing Certification |
| Quality system | 21 CFR Part 820 / QSR | ISO 13485 | ISO 13485 | ISO 13485 | ISO 13485 | QMS Ordinance (省令) |
| Device class | Class I/II/III | Class I/IIa/IIb/III | Class I/IIa/IIb/III | Class I/IIa/IIb/III/AIMD | Class A/B/C/D | Class I/II/III/IV |
| Regulatory submission | 510(k) / PMA | Technical Documentation | Technical File | Application for ARTG | MEDICS Registration | Application to PMDA |
| Clinical evidence | Clinical Performance Testing | Clinical Evaluation Report (CER) | Clinical Evaluation | Clinical Evidence | Clinical Evaluation | Clinical Study Data |
| Post-market | PMS (Post-Market Surveillance) | PSUR + PMCF | PSUR + PMCF | Post-Market Review | Post-Market Surveillance | Post-Market Studies |

### 8.2 Regulatory Terminology Namespace

```json
// locales/de-DE/regulatory.json
{
  "authorization": "Zulassung",
  "ce_marking": "CE-Kennzeichnung",
  "notified_body": "Benannte Stelle",
  "technical_documentation": "Technische Dokumentation",
  "clinical_evaluation": "Klinische Bewertung",
  "post_market_surveillance": "Marktnachbeobachtung",
  "risk_management": "Risikomanagement"
}
```

---

## 9. Right-to-Left (RTL) Language Support

### 9.1 RTL Architecture Requirements

For Arabic (Phase 5 — UAE/Saudi Arabia) and any future RTL languages (Hebrew, Persian):

**CSS Architecture:**
```css
/* Use CSS logical properties throughout */
.inspection-card {
  margin-inline-start: 1rem;    /* instead of margin-left */
  margin-inline-end: 1rem;      /* instead of margin-right */
  padding-inline: 1.5rem;
  border-inline-start: 3px solid var(--primary);
}

/* HTML dir attribute — set at root level */
/* <html dir="rtl" lang="ar"> */
```

**React RTL Context:**
```typescript
// frontend/src/contexts/DirectionContext.tsx
import { createContext, useContext } from 'react';

type Direction = 'ltr' | 'rtl';

const RTL_LANGUAGES = ['ar', 'he', 'fa'];

export const getDirection = (locale: string): Direction => {
  const lang = locale.split('-')[0];
  return RTL_LANGUAGES.includes(lang) ? 'rtl' : 'ltr';
};

// Apply to document root
document.documentElement.dir = getDirection(currentLocale);
document.documentElement.lang = currentLocale;
```

### 9.2 RTL Preparation Checklist (Pre-Arabic Launch)

- [ ] All CSS margin/padding converted to logical properties (inline-start/end, block-start/end)
- [ ] Flexbox/Grid direction-aware: `flex-direction: row` works correctly with RTL
- [ ] Icons and directional indicators mirrored for RTL (chevrons, arrows, progress indicators)
- [ ] Charts and timelines: X-axis direction correct in RTL
- [ ] Form field alignment: Input field text alignment correct (`text-align: start`)
- [ ] Table column order: Consider RTL reading order for column sequence
- [ ] Numbers: Medical/professional numbers use Western Arabic numerals (0-9) in Arabic medical context

### 9.3 RTL Testing Matrix

| Component | LTR Test | RTL Test | Notes |
|-----------|----------|----------|-------|
| Navigation sidebar | Left rail | Right rail | Direction-aware |
| Inspection result cards | L-to-R flow | R-to-L flow | Logical properties |
| Data tables | Columns L-to-R | Columns R-to-L | Header alignment |
| Date pickers | Calendar L-to-R | Calendar R-to-L | Intl.DateTimeFormat |
| Progress bars | Fills left | Fills right | CSS logical |
| Icons (chevrons) | → / ← | Mirrored | SVG/font icon flip |

---

## 10. Localization Quality Assurance

### 10.1 Translation Workflow

1. **Source string extraction**: `i18next-parser` extracts keys from codebase
2. **Translation management**: Phrase (formerly Memsource) or Lokalise — professional TMS integration
3. **Professional translation**: ISO 17100-certified medical translation agency for healthcare terminology
4. **Back-translation review**: Critical medical/safety terminology back-translated for accuracy validation
5. **In-context review**: Native-speaking SPD professional reviews translation in actual product context
6. **Regulatory terminology review**: Local regulatory affairs team reviews regulatory terminology
7. **OQLF review** (Quebec French): Additional review for Office québécois de la langue française compliance

### 10.2 Pseudo-localization Testing

Before each language launch, pseudo-localization testing validates:
- UI layout accommodates 30–40% string expansion (common for German, French vs. English)
- No hard-coded string lengths in UI components
- All strings use translation keys (no hardcoded English strings in JSX)
- Pluralization rules function correctly for each language

```bash
# Pseudo-localize for testing (extend strings ~40%)
# Tool: pseudo-localization npm package
npx pseudo-localize --input src/i18n/locales/en --output src/i18n/locales/pseudo
```

---

## 11. Document Metadata

| Field | Value |
|-------|-------|
| Author | LumenAI Product & Engineering Team |
| Review Date | Quarterly |
| Next Review | 2026-09-21 |
| Approvers | VP Product, VP Engineering, VP International Sales |
| Related Documents | LUM-GLOBAL-001 (Market Strategy), LUM-GLOBAL-005 (Multi-Region Architecture) |
