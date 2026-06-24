# Biomarker Analyser — Intended Purpose (v0.1, Phase 0 prototype)

> **Status:** governance source of truth for the biomarker analyser. Change-controlled.
> The biomarkers sub-agent prompt (`data/prompts/agents/biomarkers_sub_agent.md`) and
> `tests/test_biomarker_boundary.py` are **implementations of this document** — if this
> document changes, they change. Companion: [`BIOMARKER_SCHEMA.md`](BIOMARKER_SCHEMA.md).

This is a **personal Phase 0 prototype** — not a shipped product, not a regulated device, no
external claims. The intended purpose below is deliberately scoped so the software has **no medical
purpose** and is therefore **not a medical device** (UK/EU MDR; IMDRF / MDCG 2019-11 logic). The
prototype treats any seeded content as if clinician-signed; no actual sign-off is implied.

---

## The statement

> **"[Product] is a personal information tool that displays the results of a single blood test report
> belonging to the individual, together with the testing laboratory's own reference ranges, organised
> by body system, and provides general educational information describing what each biomarker is and
> its normal physiological function. It operates on one result set at a time. It is intended for use
> by the individual themselves, for their own information, on their own device, outside any clinical
> care setting.**
>
> **It does NOT: diagnose, screen, monitor, predict, or interpret the individual's results; state or
> imply whether a result is high, low, abnormal, or normal; relate any result to a disease or
> condition; describe what abnormal levels may indicate or cause; recommend treatment, dosing, or any
> care decision; ingest or compare more than one result set; or analyse change/trend over time. It is
> not a medical device and provides no medical advice; for any interpretation of their results the
> individual is directed to a clinician."**

**Consequence:** no medical purpose → **not a medical device → no clinical evaluation, no
classification, no Approved Body.** Every downstream control exists to keep the product true to this
statement.

---

## First-principles derivation

Built using the four-component frame from Scarlet's *Clinical Evaluation for SaMD — cover the whole
intended purpose* (patient population · clinical condition · use environment · user), gated by the
prior **"significance of information"** fork. Because clinical evaluation must cover *every* named
condition/population, **breadth is the cost driver** — and the Emerald source spans ~90 markers / ~19
categories, so the statement is kept deliberately narrow.

| Step | Decision | Why it holds the non-device line |
|------|----------|----------------------------------|
| **1 · Significance of information** | **No medical purpose** — display own values + the lab's own ranges + generic education | The root fork. Not informing/driving/diagnosing any clinical decision → not a device; no clinical evaluation owed. |
| **2 · Clinical condition** | **None.** Organised under **neutral body-system labels** (Blood & iron · Heart & circulation · Sugar & metabolism · Liver · Kidney · Thyroid · Hormones · Vitamins & minerals) | The lab's condition headers ("Diabetes Testing", "Metabolic Syndrome Testing") name a disease/syndrome — dropped. Body-system labels describe *where*, not *what disease*. |
| **3 · Intended user** | The **individual lay self-user** | No clinician user, no shared-care workflow. |
| **4 · Use environment** | **Personal / non-clinical** (own device; LangGraph UI + Telegram) | Not used in any care setting. |
| **5 · Patient population** | The **single individual** (self), adult | One self-user, not a population claim — no "patient" in the regulatory sense. |
| **6 · Inputs / outputs** | **Single** accredited report in; value + lab's range + body-system grouping + generic education out | Single result set → longitudinal monitoring is *structurally* impossible. Education = definition + physiological function only. |

---

## The verb ledger (locked)

A copy edit that swaps a safe verb for a trigger verb is a **re-classification event**, not a content
tweak.

- **Safe:** *displays, shows, presents, defines, educates, lists, organises, routes, contextualises.*
- **Trigger (forbidden at Phase 0):** *interprets, diagnoses, screens, monitors, predicts, recommends,
  indicates risk, scores, flags high/low, trends.*

---

## The education boundary (Step 6 line — the live drift edge)

Generic education from the DB glossary (`get_biomarker_education`) describes **what a biomarker is**
and its **normal physiological function**, and stops *before* any consequence-of-abnormal.

- ✅ Allowed: *"LDL is a lipoprotein that carries cholesterol around the body. Cholesterol is used to
  build cells and make hormones."*
- ⛔ Blocked from the glossary tool: *"High LDL is linked to heart disease." · "Your level suggests…"*

This baseline is **extended — not removed —** by the vetted-knowledge amendment below.

---

## Amendment: vetted knowledge grounding (Emerald RAG)

The agent may additionally serve **vetted, source-attributed general knowledge** from Emerald's
public knowledge base via `get_biomarker_knowledge` (pgvector RAG over scraped markdown). This content
*may* include what elevated/low levels **generally** indicate.

**Why this stays outside the device definition (first-principles):** the medical-purpose hinge is
whether software *processes a specific individual's data to produce a patient-specific output for a
clinical purpose*. A static, general, source-attributed knowledge article is **general medical
information** — the same category as a textbook or the lab's own leaflet — not applied to the
individual. A library is not a device. The risk lives entirely in **juxtaposition**: placing a
general "elevated LDL means X" *next to* the user's own "LDL 145" in the same answer reconstructs an
individualised interpretation. So the controllable variable is the **serving contract**, not the
corpus.

**The load-bearing control is the no-bridging rule:**

- ✅ Allowed: *"Per Emerald's knowledge base, elevated LDL is generally associated with cardiovascular
  risk."* (general, attributed, stands alone)
- ⛔ Still blocked: bridging it to the user's number — *"your 145 is elevated, which means…"* — or any
  verdict / interpretation / diagnosis / trend on **their** value.

This is a deliberate scope decision for the prototype: the corpus is rich; the boundary is enforced at
serving time by the sub-agent prompt's no-bridging contract.

---

## Ingestion: PDF → structured results (does not change the purpose)

A lab report can be loaded from a **PDF** (`whoopdata/biomarkers/pdf_ingest.py`): digital PDFs are
read as text, scanned ones rendered to page images, then an LLM produces structured rows mapped to
the **neutral body-system categories** (disease/condition headers are dropped, same as before). This
is an *ingestion* mechanism only — it does not add interpretation, prediction, or a medical purpose;
the output is the same value + lab's-own-range + body-system data the analyser has always displayed.

Two controls apply:
- **Human confirmation before write.** Extraction is read-only; the destructive truncate-and-load
  only runs after the user confirms a preview (CLI `--commit`; Telegram confirm button). This guards
  against an OCR misread silently overwriting the stored report.
- **Single timepoint preserved.** The write path is the same truncate-and-load
  (`whoopdata/biomarkers/ingest_service.py` → `crud.replace_report`), so only one result set exists.

---

## Operative spec for code

The **"does NOT" list above is the specification** for:
- the biomarkers sub-agent prompt (`data/prompts/agents/biomarkers_sub_agent.md`), which is the
  sole guardrail: it instructs the model to show values + the lab's own range, generic education, and
  vetted general (Emerald) knowledge with attribution — never bridging the latter to the user's own
  value, and referring any interpretation of *their* result to a clinician,
- the data layer: `lab_status` is stored but **never surfaced** by CRUD/tools, and the single
  result set is enforced by truncate-and-load (`whoopdata/crud/biomarker.py`) — this invariant is
  tested by `tests/test_biomarker_boundary.py`,
- the knowledge layer: vetted Emerald markdown is embedded into pgvector
  (`whoopdata/knowledge/ingest_biomarker_kb.py`) and served read-only as general, source-attributed
  passages by `get_biomarker_knowledge` (`whoopdata/knowledge/biomarker_kb.py`),
- the ingestion layer: PDF→structured extraction (`whoopdata/biomarkers/pdf_ingest.py`) is read-only
  and writes only via the shared, confirmed truncate-and-load path
  (`whoopdata/biomarkers/ingest_service.py`).

If any line here changes, those implementations must change with it.
