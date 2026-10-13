# NUXEL — Trademark Clearance Report

> **Prepared by:** Nuxel Legal & Naming Team
> **Date:** 2026-08-11
> **Scope:** word mark **NUXEL** in Nice class 9 (computer software, operating systems, firmware) and class 38 (telecommunications).
> **Status:** **⚠️ Pending-online-access for the three core registries (EUIPO/USPTO/UKIPO); ecosystem registries completed.**

---

## 1. Executive Summary

A clearance search for the word mark **NUXEL** was initiated across the three
core trademark registries (EUIPO, USPTO, UKIPO) for Nice classes 9 and 38, plus
a sweep of common open-source/package ecosystems (GitHub, npm, PyPI, Homebrew,
Flathub) and the WIPO Global Brand Database.

- **Ecosystem registries** were fully queried and completed (see §4). No
  package-ecosystem hit uses the exact name `nuxel` at any publication scale,
  and no active project appears to brand itself "Nuxel". The closest candidates
  are small/abandoned GitHub repositories, none of which operate a commercial
  OS product under the name.
- **The three trademark registries (EUIPO/USPTO/UKIPO) were NOT directly
  queryable from this build sandbox.** Their public search UIs are
  JavaScript-driven portals (and USPTO additionally now gates its TSDR bulk API
  behind a registered API key). Those searches must be re-run in a browser.
  The exact URLs and query strings to use are documented in §2–§3, and the
  result is recorded as **Found-Unknown / Pending-online-access**.

**Preliminary lean (non-binding):** no material pre-existing "Nuxel" brand in the
package ecosystem is an obstacle, and the word is likely to be **distinctive**
for phone-OS software. However, **a binding clearance cannot be issued until the
EUIPO/USPTO/UKIPO portal searches below are completed** (including a
filing-number and phonetic/bilingual check). If EUIPO shows a conflicting live
mark in class 9/38 (common in operating-system/software classes), a
**distinctive stylized logo + different composite mark** should be adopted.

---

## 2. EUIPO search (TMview / eSearch)

- **Registry:** European Union Intellectual Property Office (EUIPO)
- **URL:** `https://euipo.europa.eu/eSearch/#basic/1+1+1+1/nuxel/...`
  (also `https://www.tmdn.org/tmview/`)
- **Query to run:**
  - Basic search term: `nuxel`
  - Fields: name (wordmark), class 9 and class 38
  - Also search phonetically similar: `nuxl`, `nuxell`, `nuxelé`, `nuksel`
  - Also search `nuxel*` prefix and `*xel` suffix to broaden.
- **Sandbox result:** ❌ **Unreachable** — eSearch/TMview backend reset the
  connection (`curl 56 – connection reset by peer`) for headless requests.
  EUIPO's front-end HTML loads but the results are loaded by an Angular SPA +
  protected API. **Mark as: Pending-online-access (manual browser search).**

**Record (EUIPO):**

| Field | Value |
|---|---|
| Result | **Pending** (unable to query programmatically) |
| Filing # | n/a |
| Owner | n/a |
| Classes | 9, 38 requested |
| Status | n/a |
| Notes | Run `https://euipo.europa.eu/eSearch/#basic/...` in a browser; record any EU word mark equal or phonetically similar to NUXEL. |

---

## 3. USPTO and UKIPO searches

### 3.1 USPTO (US Patent & Trademark Office)

- **Registry:** USPTO
- **URLs:**
  - Trademark Search portal: `https://tmsearch.uspto.gov/search/search-information`
  - TSDR: `https://tsdr.uspto.gov/` (status/search documents)
  - Bulk/API: `https://developer.uspto.gov/api-catalog` (requires registered API key as of Oct 2024+; TSDR bulk APIs now gated).
- **Query to run:** live wordmark `NUXEL` in class 9 and class 38; record Live / Dead / Registered status for any hit. Also run phonetic `NUXEL/PIXEL` (very similar-sounding — document any `*XEL`-ending marks) and `XEL`/`UXEL` variants.
- **Sandbox result:** ❌ **Unreachable** — `tmsearch.uspto.gov` is a JS SPA; the
  mark-search API endpoint is not publicly queryable without the browser
  workflow, and TSDR status/bulk data requires an API key (which we do not hold/reactivate in the sandbox). **Mark as: Pending-online-access (manual browser search).**

**Record (USPTO):**

| Field | Value |
|---|---|
| Result | **Pending** (needs browser/portal use) |
| Filing # | n/a |
| Owner | n/a |
| Classes | 9, 38 requested |
| Status | n/a (Live / Dead / Registered to be recorded) |
| Notes | Watch for any `NUXEL` or near `NUXEL` (e.g. `PIXEL`, `NUX`, `NUKEL`) marks; check both word and design registrations. |

### 3.2 UKIPO (UK Intellectual Property Office)

- **Registry:** UKIPO
- **URL:** `https://trademarks.ipo.gov.uk/ipo-tmtext` (TM text/word search);
  number search at `https://www.ipo.gov.uk/types/tm/t-os/t-find.htm`
- **Query to run:** `nuxel` in classes 9 and 38; also `nuxel*`.
- **Sandbox result:** ❌ **Unreachable** — UKIPO trademark pages returned
  `403 Forbidden` to the sandbox HTTP client. **Mark as: Pending-online-access (manual browser search).**

**Record (UKIPO):**

| Field | Value |
|---|---|
| Result | **Pending** (needs browser/portal use) |
| Filing # | n/a |
| Owner | n/a |
| Classes | 9, 38 requested |
| Status | n/a |
| Notes | Run `https://trademarks.ipo.gov.uk/ipo-tmtext` for `nuxel` class 9 + 38; any live UK national registration requires attention. |

### 3.3 WIPO Global Brand Database (supplementary)

- **URL:** `https://branddb.wipo.int/en/quicksearch?brand=nuxel`
- **Sandbox result:** Portal is also a JS SPA; the page loaded (HTTP 200) but
  results are rendered client-side and not extractable headlessly. Mark as
  **Pending-online-access (manual browser search)** — this DB aggregates
  Madrid Protocol international registrations (which are directly relevant to
  EU-wide protection) so it is a useful cross-check alongside EUIPO.

---

## 4. Ecosystem / package-registry search (COMPLETED)

> These searches completed successfully in the sandbox. A hit here does not
> constitute a trademark registration, but flags brand-name collisions to
> avoid confusion or prior-use disputes.

### 4.1 GitHub repositories named `nuxel` / `NUXEL`

Queried `https://api.github.com/search/repositories?q=nuxel` (and `NUXEL`).
**Total: 18 repositories.** Near-name set and notable entries:

| Repository | Description | Stars | Relevance to Nuxel OS |
|---|---|---|---|
| `mmshooreshi/nuxel` | "Pixel-perfect, Dockerized Nuxt.js starter template" | 1 | Low — unrelated Node/Docker web template; abandoned (last update 2024-05). |
| `ma1uta/nuXel` | "simple application library (mainly scala language playground)" | 0 | Low — Scala hobby project; no OS/telecom relation. |
| `NikolayG92/Nuxel` | no description; Apache-2.0 | 0 | Very low. |
| `Nuxel-Dev/Nuxel-Dev` | GitHub profile config | 0 | Low — personal profile; no products. |
| `NuxeLSadew/NuxeL`, `NuxeLSadew/NuxeLSadew` | personal profile/config | 0 | Low. |
| `botvi/nuxel_studio`, `somerandomguyfromindai/NUXELAND`, `espice/nuxeland`, `SCO21/NUXELIT_FRONT`, `Dangs111/NUXELA_WEB`, `NUXELIT_ADMIN_FRONTEND` | unlisted/site/template projects | 0 | Very low — none is a commercial OS or telecom brand. |
| `MJperx/nuxel-releases`, `derclin/SITE_NUXELL` | unlisted | 0 | Very low. |

**Finding:** No GitHub repository brands itself as a "Nuxel" phone operating
system, and none operates at any meaningful scale for the OS/telecom space.
No prior-use or trademark-confusion concern identified from GitHub alone.

### 4.2 npm registry

- **Query:** `https://registry.npmjs.org/-/v1/search?text=nuxel`
- **Result:** **0 packages** found. No npm module named or containing `nuxel` is published.

### 4.3 PyPI (Python package index)

- **Query:** `https://pypi.org/pypi/nuxel/json` → **HTTP 404** (package does not exist).
  PyPI XML-RPC search is deprecated, so web UI search is the definitive check,
  which currently returns no `nuxel` package.
- **Result:** **None** — no Python package named `nuxel`.

### 4.4 Homebrew

- **Query:** `https://formulae.brew.sh/api/formula.json`
- **Result:** **0 formulas** contain `nuxel`. No Homebrew cask/formula named `nuxel`.

### 4.5 Flathub

- **Query:** `https://flathub.org/api/v2/appstream`
- **Result:** **0 apps / IDs** contain `nuxel`. No Flatpak app ID/flatpak-branded `nuxel`.

### 4.6 Consolidation

| Ecosystem | Query | Result |
|---|---|---|
| GitHub (repos) | `nuxel` | 18 repos; no OS/telecom brand; all tiny/inactive |
| npm | `nuxel` | **None** |
| PyPI | `nuxel` | **None** (404) |
| Homebrew | `nuxel` | **None** |
| Flathub | `nuxel` | **None** |

---

## 5. Findings tables per registry (consolidated)

| Registry | Query | Result | Filing # | Owner | Classes | Status | Notes |
|---|---|---|---|---|---|---|---|
| EUIPO | `nuxel` class 9+38 | **Found-Unknown → Pending** | n/a | n/a | 9, 38 | Pending (portal) | eSearch/TMview unreachable headlessly; run in browser. |
| USPTO | `NUXEL` class 9+38 | **Found-Unknown → Pending** | n/a | n/a | 9, 38 | Pending (portal > key) | tmsearch is JS; TSDR bulk needs API key. |
| UKIPO | `nuxel` class 9+38 | **Found-Unknown → Pending** | n/a | n/a | 9, 38 | Pending (portal) | 403 from sandbox; run in browser. |
| WIPO (Madrid) | `nuxel` | **Found-Unknown → Pending** | n/a | n/a | 9, 38 | Pending (portal) | JS SPA; use as cross-check for EU protection. |
| GitHub | `nuxel` | **Found** (18) | n/a | mixed | n/a | Active/Dead (all tiny/inactive) | No OS/telecom brand collision; lowest risk. |
| npm | `nuxel` | **None** | n/a | — | — | — | Clear. |
| PyPI | `nuxel` | **None** | n/a | — | — | — | Clear. |
| Homebrew | `nuxel` | **None** | n/a | — | — | — | Clear. |
| Flathub | `nuxel` | **None** | n/a | — | — | — | Clear. |

---

## 6. Recommendation

**Before acting on a final name decision, complete the three-portal manual
searches (§2–§3) and record the Live/Dead/Registered status.** The exact
browser queries to run are:

1. EUIPO  → `https://euipo.europa.eu/eSearch/#basic/1+1+1+1/nuxel`
2. USPTO  → `https://tmsearch.uspto.gov/search/search-information` (basic live word `NUXEL`)
3. UKIPO  → `https://trademarks.ipo.gov.uk/ipo-tmtext` (term `nuxel`)
4. WIPO   → `https://branddb.wipo.int/en/quicksearch?brand=nuxel`

**Interim recommendation (conditional on EUIPO/USPTO/UKIPO cleanliness):**

- If the pending registry checks come back **clear (None Live) for class 9 and
  class 38**, the **NUXEL** word mark appears **clear to use** in
  software/OS/firmware (class 9) and telecommunications (class 38). No
  ecosystem package uses the exact name at any scale, increasing distinctiveness
  and reducing prior-use confusion.
- **If EUIPO shows any Live conflicting mark** in class 9 or 38 (operating
  systems/software and telecoms are high-traffic classes), do **not** rely on
  the bare word mark. Adopt a **distinctive stylized logo plus a composite mark**
  (e.g. a unique word+device combination with the Nuxel waveform/logo shown at
  `assets/nuxel-logo.*`) and consider a descriptive-but-distinctive alternative
  (e.g. adding a fanciful suffix) to improve searchability and avoid confusion
  with `PIXEL`/`NUX`-style marks.

**Recommended next steps (blocking → non-binding):**
1. *(Blocking)* Run the four browser searches; record results in this doc.
2. *(Recommended)* File EUIPO class 9 + class 38 word + device applications;
   consider a Madrid international designation for EU-wide breadth.
3. *(Recommended)* Register `nuxel` project/package names on npm/PyPI/Flathub to
   protect the brand namespace ahead of release (currently all free).
4. *(Recommended)* Secure github organizations (`nuxel`, `nuxel-os`) for the
   project once the classification is confirmed.

---

*This report is an informational clearance aid, not a legal opinion. Seek
qualified trademark counsel before filing any applications.*
