# International Readiness Scorecard — LumenAI Global Markets

**Document ID:** LUM-GLOBAL-009  
**Version:** 1.0  
**Status:** Planning  
**Milestone:** P20 — International Expansion & Global Regulatory Readiness  
**Classification:** Executive Confidential  

> **Scoring Framework:** Each market is scored across 6 dimensions (1–5 scale, 5 = highest readiness). Maximum total score: 30 points.
> 
> **Recommendations:**
> - **Ready** (24–30 points): Market entry can proceed; known requirements well-addressed
> - **Conditionally Ready** (15–23 points): Market entry feasible with defined investments; proceed with clear action plan
> - **Not Ready** (< 15 points): Significant gaps; market entry deferred until investments completed

---

## Scoring Dimensions

| Dimension | Definition | Score 1 | Score 5 |
|-----------|-----------|---------|---------|
| **Regulatory** | Pathway clarity, documentation readiness, timeline feasibility | Unknown pathway; no documentation | Clear pathway; documentation ready; timeline ≤ 12 months |
| **Security** | Regional security compliance posture; certifications required | Major security gaps; no required certifications | All required certifications in place; no gaps |
| **Infrastructure** | Regional cloud availability; data residency capability | No regional infrastructure; no data residency capability | Full regional stack deployed; data residency enforced |
| **Localization** | Language support; SPD terminology; date/currency/measurement | No localization; multiple blockers | Full localization live; all regional terminology ready |
| **Commercial** | Market opportunity; competitive landscape; channel readiness | Minimal opportunity; no channel; high competition | Large opportunity; clear channel; favorable competition |
| **Support** | Regional support capability; time zone; language coverage | No regional support; major TZ gap | Full regional support; same-TZ coverage; native language |

---

## 1. Canada

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 4 | Health Canada MDL Class II; streamlined with FDA 510(k) reference; MDSAP leverage. Pathway clear; 6–12 month timeline. Minor gap: French bilingual labeling for national market. |
| **Security** | 3 | Core controls active (AES-256, TLS, tenant isolation). SOC 2 Type II in progress. Gap: PIPEDA-specific procedures, Quebec Law 25 PIA, ca-central-1 region not yet active. |
| **Infrastructure** | 3 | AWS ca-central-1 (Montreal) available and suitable; architecture designed; not yet activated. Canadian data residency requires ca-central-1 activation for Quebec/provincial compliance. |
| **Localization** | 4 | English primary — immediately deployable across 8 provinces. French (Quebec) is a 3–6 month investment; terminology alignment needed (CSA Z314, provincial French). Currency: CAD configurable. |
| **Commercial** | 5 | Large mature market; HealthPRO/Medbuy GPO channels; private hospital sector fast-moving. Censitrac, Epic, Cerner all deployed — integrations planned. Adjacent time zones. Strong reference leverage from US customers. |
| **Support** | 4 | Current US team covers ET/PT zones (Canada-compatible). French (Quebec) support is a gap. Regional CSM identified for Year 1. RL6/RLDatix integration needed for Canadian patient safety context. |

**Total Score: 23 / 30**
**Recommendation: CONDITIONALLY READY**

**Key Conditions for Launch:**
1. Health Canada MDL submission preparation complete
2. AWS ca-central-1 activation with Canadian data residency controls
3. French (Quebec) localization (Phase 1) timeline confirmed
4. PIPEDA/Quebec Law 25 DPA template executed for early customers

---

## 2. United Kingdom

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 3 | UKCA pathway clear; UK MDR 2002 well-documented; UK Approved Body identification underway. DTAC, DSP Toolkit, DCB0129 required for NHS — significant additional effort. 12–18 month timeline. CE Mark transitional recognition possible. |
| **Security** | 3 | Core controls strong. Missing: Cyber Essentials Plus (HIGH priority for NHS), DSP Toolkit registration, CREST penetration testing, ISO 27001 in progress. These are achievable within 6 months. |
| **Infrastructure** | 3 | AWS eu-west-2 (London) well-established; architecture designed for UK data residency (UK GDPR post-Brexit). Not yet activated. UK GDPR DPA template in preparation. |
| **Localization** | 4 | English primary — immediately deployable. UK-specific terminology (Theatre, HSDU, decontamination, sterilisation) requires en-GB locale additions. Currency: GBP configurable. DSP Toolkit and DCB0129 terminology alignment required. |
| **Commercial** | 4 | NHS is a massive market; post-pandemic surgical backlog driving investment; strong DATIX, Q-Pulse, Censitrac ecosystem integrations planned. NHS procurement frameworks provide structured pathway. Competitive landscape manageable. |
| **Support** | 3 | Time zone manageable (GMT/BST vs ET — 5-hour offset). Requires UK-based CSM. NHS customer success requires NHS Domain knowledge specialist. DATIX, Q-Pulse integrations needed before enterprise NHS deployment. |

**Total Score: 20 / 30**
**Recommendation: CONDITIONALLY READY**

**Key Conditions for Launch:**
1. Cyber Essentials Plus certification (Q2 Year 1)
2. NHS DSP Toolkit registration (Q1 Year 1)
3. EU-west-2 (London) AWS stack activation
4. UK Approved Body engagement initiated (UKCA pathway)
5. DCB0129 Clinical Risk Management file preparation

---

## 3. European Union (Germany as Lead)

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 2 | EU MDR (Regulation 2017/745) is the most demanding regulatory pathway. Notified Body engagement required; NB capacity constraints mean 18–30 months to CE Mark. CER, PMCF, EUDAMED registration, EU AR — all not yet started. Significant investment required. |
| **Security** | 3 | Core controls strong. ISO 27001 needed (not yet certified). GDPR DPIA required. EU-specific security: ENISA guidance, MDCG 2019-16 compliance needed for NB. Achievable within 12 months with investment. |
| **Infrastructure** | 3 | AWS eu-west-1 (Ireland) + eu-central-1 (Frankfurt) architecture designed; not yet activated. GDPR cross-border controls planned. EEA-internal DR strategy (eu-west-1 → eu-central-1) maintains GDPR compliance. |
| **Localization** | 2 | German UI, documentation, and support required for Germany market. French, Dutch for other EU markets. Current English-only is insufficient. German localization (Phase 2) is a significant investment — technical and medical terminology. Not yet started. |
| **Commercial** | 4 | Germany alone is a large market (1,900+ hospitals); EU aggregated opportunity is very large. Distributor partner model identified for Germany. Public tender process is complex but structured. Getinge T-DOC integration critical. Long sales cycles. |
| **Support** | 2 | No German-language support currently. CET/CEST time zone (1–6 hour offset from US ET). EU-based CSM required. German regulatory and clinical expertise needed. Distributor model partially offsets support gap. |

**Total Score: 16 / 30**
**Recommendation: CONDITIONALLY READY (Tier 2 — 12–24 months)**

**Key Conditions for Launch:**
1. Notified Body engagement and CE MDR submission preparation (18–24 month track)
2. German language localization complete
3. German distribution partner contracted and certified
4. ISO 27001 certification (required for NB assessment)
5. GDPR DPA and DPIA complete
6. Getinge T-DOC integration live

---

## 4. Australia

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 4 | TGA ARTG pathway clear; MDSAP participation by TGA is significant accelerator. Class IIb pathway (higher than expected) but well-documented. Australian Sponsor required (manageable). 12-month timeline with MDSAP. |
| **Security** | 3 | Core controls strong. IRAP assessment needed for government hospital sector (state health depts). SOC 2 Type II sufficient for private hospital sector. AWS ap-southeast-2 is IRAP-assessed infrastructure. Timeline: IRAP 3–6 months. |
| **Infrastructure** | 3 | AWS ap-southeast-2 (Sydney) available and well-established; architecture designed; not yet activated. Australian Privacy Act data residency requires ap-southeast-2 activation. NDB breach notification procedure needed. |
| **Localization** | 5 | English primary — no localization investment needed for Australian market entry. AU-specific terminology (Theatre, CSSD, AS/NZS 4187 terminology) requires en-AU locale adjustments — minimal effort. Currency: AUD configurable. |
| **Commercial** | 4 | Strong market; private hospital sector (Ramsay, Healthscope) can move faster than public. AS/NZS 4187:2014 compliance driver. Riskman, DATIX, Censitrac integrations planned. ACORN/ACIPC association partnerships high value. |
| **Support** | 3 | AEST/AEDT time zone (14–16 hours from ET) is the biggest operational challenge. Australian CSM required. Follow-the-sun model addresses this. English language mitigates other support complexity. |

**Total Score: 22 / 30**
**Recommendation: CONDITIONALLY READY**

**Key Conditions for Launch:**
1. TGA ARTG application submission (MDSAP audit required first)
2. AWS ap-southeast-2 activation with Privacy Act data residency controls
3. Australian Sponsor entity established
4. Riskman and Censitrac integrations live (required for competitive positioning in AU)
5. Australian CSM hired with CSSD/healthcare domain background

---

## 5. Singapore

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 4 | HSA pathway well-defined; Class B/C registration via MEDICS; English documentation accepted; FDA clearance serves as strong reference. 6–12 month timeline. Straightforward among Asia markets. |
| **Security** | 4 | Core controls strong. CSA STAR Level 1 self-assessment is quick to complete. PDPA 3-day breach notification is stringent — procedure must be in place. Overall security posture well-suited to Singapore regulatory expectations. |
| **Infrastructure** | 4 | AWS ap-southeast-1 (Singapore) is a mature, well-established region; excellent performance. PDPA data residency manageable. Architecture designed; activation straightforward. |
| **Localization** | 5 | English is the official business language of Singapore; no translation required for professional users. UI and documentation deployable immediately in English. Currency: SGD configurable. |
| **Commercial** | 3 | Smaller absolute market (30 public + 20 private hospitals) but strategically important as ASEAN gateway. Epic NUHS deployment is a strong reference integration opportunity. iHIS/Synapxe is complex but high value. SingHealth cluster is a marquee customer target. |
| **Support** | 3 | SGT time zone (12–13 hours from ET). Singapore-based CSM (or APAC-based in Singapore) required. English language simplifies support. PDPC 3-day breach notification procedure requires 24/7 incident response capability. |

**Total Score: 23 / 30**
**Recommendation: CONDITIONALLY READY**

**Key Conditions for Launch:**
1. HSA MEDICS registration initiated
2. AWS ap-southeast-1 activation
3. PDPA breach notification procedure (3-day) operational
4. CSA STAR Level 1 self-assessment complete
5. iHIS/Synapxe API access pathway identified (MOH Holdings engagement)

---

## 6. Japan

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 1 | PMDA/MHLW pathway complex; Japanese-language documentation mandatory; DMAH (designated MAH) required for foreign manufacturer; 24–36 months to marketing certification. QMS Ordinance (separate from ISO 13485) requires Japan-specific compliance. Not yet initiated. |
| **Security** | 3 | Core controls meet Japanese requirements. APPI 2022 breach notification (30 days) manageable. NISC guidelines achievable. No Japan-specific certification required beyond ISO 27001 (which is global). |
| **Infrastructure** | 3 | AWS ap-northeast-1 (Tokyo) is a mature, full-featured region. APPI data residency manageable with Tokyo region activation. Architecture straightforward. Infrastructure readiness is not the bottleneck — regulatory and localization are. |
| **Localization** | 1 | Full Japanese localization required (all UI, documentation, support, regulatory submissions). Japanese medical terminology (滅菌, 中央材料室, etc.) must be accurate. Kanji/Hiragana/Katakana all required. Honorific register. Not yet started. Significant investment: 12–18 months for complete localization. |
| **Commercial** | 3 | Very large market (8,200+ hospitals) but distribution through Japanese medical distributors is complex; relationship-driven; trust built over years. Distributor/DMAH partner identification in early stages. Long sales cycles (2–3 years common for novel SaaS). |
| **Support** | 1 | JST time zone (13–14 hours from ET); Japanese-language support required. No current Japanese-language capability in LumenAI team. Distributor must provide Japanese support. Significant gap. |

**Total Score: 12 / 30**
**Recommendation: NOT READY**

**Gap Plan:**
1. DMAH partner identification and agreement (Year 2)
2. Japanese localization investment (Year 2–3)
3. PMDA pre-consultation (Year 2)
4. Japanese marketing certification preparation (Year 3 target)
5. Japanese-language support through DMAH (Year 3)

---

## 7. South Korea

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 3 | MFDS pathway manageable; Class II likely; 12–18 months with Korean regulatory agent; MFDS accepts ISO 13485 and references FDA/CE documentation. Korean RAH required. Not yet started but straightforward once initiated. |
| **Security** | 3 | Core controls meet Korean requirements. PIPA 2023 breach notification (72 hours) requires procedure. Korean data in ap-northeast-2 (Seoul) — manageable. ISO 27001 (planned) satisfies MFDS security expectations. |
| **Infrastructure** | 3 | AWS ap-northeast-2 (Seoul) available. PIPA data residency manageable. Architecture straightforward. Not yet activated but infrastructure not a blocker. |
| **Localization** | 2 | Korean UI, documentation, and support required. Korean medical terminology and professional register (합쇼체 formal) required. Korean localization (Phase 3) investment of 6–9 months. Not yet started. |
| **Commercial** | 3 | Strong tertiary hospital market (Samsung Medical Center, Asan, SNUH); Korean health systems are early technology adopters. Korean regulatory agent doubles as commercial partner in many cases. Public hospital procurement complex; private faster. |
| **Support** | 2 | KST time zone (13–14 hours from ET). Korean-language support required. Distributor provides primary support with LumenAI escalation. Manageable in distributor model but gap exists. |

**Total Score: 16 / 30**
**Recommendation: CONDITIONALLY READY (Tier 2 — 12–24 months)**

**Key Conditions for Launch:**
1. Korean regulatory agent (RAH) contracted
2. Korean localization complete
3. MFDS medical device registration submitted
4. AWS ap-northeast-2 activation
5. Korean distribution partner contracted
6. Korean-language support through distributor

---

## 8. UAE

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 2 | Multiple regulatory authorities (MOHAP, DHA, DOH) with separate requirements; no unified SaMD framework; CE/FDA reference accepted but complex multi-authority navigation; 12–24 months. Arabic documentation requirements. |
| **Security** | 3 | Core controls strong. UAE PDPL 72-hour breach notification manageable. NCA ECC (Essential Cybersecurity Controls) compliance required for health sector entities. ISO 27001 covers most requirements. |
| **Infrastructure** | 2 | AWS me-south-1 (Bahrain) is closest; AWS me-central-1 (UAE) available but limited services. Full regional stack for UAE may require me-south-1 with contractual data residency commitments. UAE healthcare sector may prefer in-country hosting. |
| **Localization** | 2 | Arabic UI required for full market penetration; RTL support needed; English accepted for professional/clinical UI in private hospitals but regulatory submissions require Arabic components. Phase 5 localization — not started. |
| **Commercial** | 3 | Growing market; international hospital operators present (Cleveland Clinic, Mediclinic, NMC); Vision 2030 healthcare investment. Dubai Health Authority digital health agenda active. Smaller absolute market than UK/AU. |
| **Support** | 2 | GST time zone (8–9 hours from ET). Arabic-language support desired. Complex multi-authority navigation requires in-country legal/regulatory support. Distributor model necessary. |

**Total Score: 14 / 30**
**Recommendation: NOT READY (Tier 3)**

**Gap Plan:**
1. Multi-authority regulatory navigation strategy (Year 2)
2. Arabic localization (RTL) investment (Year 2–3)
3. UAE distributor/legal entity identification
4. AWS me-central-1 data residency assessment
5. UAE PDPL DPA framework

---

## 9. Saudi Arabia

### Dimension Scores

| Dimension | Score (1–5) | Rationale |
|-----------|------------|-----------|
| **Regulatory** | 2 | SFDA MDMA process active but Arabic documentation required; local sponsor/agent mandatory; healthcare data localization pressure; 18–30 months. Vision 2030 is driving SFDA modernization but process remains complex. |
| **Security** | 3 | Core controls strong. NCA ECC (National Cybersecurity Authority Essential Cybersecurity Controls) compliance required for Saudi health sector. Saudi PDPL 72-hour breach notification. ISO 27001 substantially covers NCA ECC expectations. |
| **Infrastructure** | 1 | Saudi Arabia strongly prefers in-country data hosting; no AWS Saudi region yet (AWS me-south-1 Bahrain is closest; AWS has announced Saudi Arabia region — timing uncertain). In-country hosting requirement may necessitate alternative cloud provider (AWS, Microsoft Azure, local data center). Significant infrastructure gap. |
| **Localization** | 1 | Arabic mandatory for UI, regulatory submissions (Arabic summary required), privacy policy, and customer support. RTL UI required. Phase 5 localization — not started. Modern Standard Arabic + Gulf dialect considerations. |
| **Commercial** | 3 | Large and growing market; MOH-Cerner national EHR deployment is a strategic integration opportunity. Vision 2030 healthcare privatization driving digital investment. Complex procurement (MOH, National Guard, Aramco — separate procurement systems). |
| **Support** | 1 | AST time zone (7–8 hours from ET). Arabic-language support required. Local sponsor/agent required for regulatory and commercial operations. Significant support capability gap. |

**Total Score: 11 / 30**
**Recommendation: NOT READY (Tier 3)**

**Gap Plan:**
1. Monitor AWS Saudi Arabia region availability
2. Arabic localization investment (Year 2–3)
3. SFDA sponsor/agent identification
4. Saudi PDPL compliance framework
5. NCA ECC compliance assessment
6. MOH-Cerner integration pathway assessment

---

## 10. Consolidated Scorecard Summary

| Market | Regulatory | Security | Infrastructure | Localization | Commercial | Support | **Total** | **Recommendation** |
|--------|-----------|----------|----------------|--------------|------------|---------|-----------|-------------------|
| **Canada** | 4 | 3 | 3 | 4 | 5 | 4 | **23** | CONDITIONALLY READY |
| **UK** | 3 | 3 | 3 | 4 | 4 | 3 | **20** | CONDITIONALLY READY |
| **EU (Germany)** | 2 | 3 | 3 | 2 | 4 | 2 | **16** | CONDITIONALLY READY |
| **Australia** | 4 | 3 | 3 | 5 | 4 | 3 | **22** | CONDITIONALLY READY |
| **Singapore** | 4 | 4 | 4 | 5 | 3 | 3 | **23** | CONDITIONALLY READY |
| **Japan** | 1 | 3 | 3 | 1 | 3 | 1 | **12** | NOT READY |
| **South Korea** | 3 | 3 | 3 | 2 | 3 | 2 | **16** | CONDITIONALLY READY |
| **UAE** | 2 | 3 | 2 | 2 | 3 | 2 | **14** | NOT READY |
| **Saudi Arabia** | 2 | 3 | 1 | 1 | 3 | 1 | **11** | NOT READY |

---

## 11. Priority Investment Areas by Market

### Tier 1 Priorities (to achieve Tier 1 launch)

**Canada:**
- AWS ca-central-1 activation
- Health Canada MDL preparation
- French (Quebec) localization

**Australia:**
- TGA ARTG submission (post-MDSAP)
- AWS ap-southeast-2 activation
- Riskman integration

**Singapore:**
- HSA MEDICS registration
- AWS ap-southeast-1 activation
- PDPA 3-day breach notification procedure

**UK:**
- Cyber Essentials Plus certification
- NHS DSP Toolkit registration
- UK Approved Body engagement (UKCA)

### Tier 2 Priorities (to achieve Tier 2 launch)

**EU/Germany:**
- Notified Body selection and engagement
- German localization
- German distribution partner

**South Korea:**
- Korean RAH appointment
- Korean localization
- MFDS submission

### Cross-Cutting Investments (All Markets)

| Investment | Markets Served | Timeline |
|------------|----------------|----------|
| ISO 27001 certification | EU, UK, AU, SG, KR, all | Q4 Year 1 |
| MDSAP audit | US, CA, AU, JP | Q2 Year 1 |
| SOC 2 Type II | US, CA, AU, SG | Q3 Year 1 |
| CREST penetration testing | UK, EU, AU | Q3 Year 1 |
| International IR runbook | All markets | Q2 Year 1 |
| Regional AWS activation | Per market | At launch |

---

## 12. Document Metadata

| Field | Value |
|-------|-------|
| Author | LumenAI International Expansion Team |
| Review Date | Quarterly |
| Next Review | 2026-09-21 |
| Approvers | CEO, CRO, CTO, Chief Regulatory Officer |
| Related Documents | LUM-GLOBAL-001 through LUM-GLOBAL-008 |
| Distribution | Executive Team, Board (upon request) |
