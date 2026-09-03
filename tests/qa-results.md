# BurpLab CTF QA Results

**Date:** 2026-09-02  
**Scope:** Testing and reporting only; no implementation changes  
**Database:** Isolated temporary database recreated from the current schema and seed  
**Result:** 13/13 intended workflows passed; 12/12 applicable hint reviews passed; 13/13 client-source inspections passed; QA-01 resolved and reverified

## Method and Limitations

This pass used the blueprint's three-perspective structure:

- **Test A — Normal student:** Follow the intended browser/Burp HTTP sequence, recover the flag only through that sequence, and submit it through the normal challenge endpoint.
- **Test B — Beginner:** Review the progressive hints in order and determine whether they lead a stuck beginner from the starting action to the intended observation without requiring outside knowledge.
- **Test C — Source inspection:** Search rendered challenge HTML, raw templates, JavaScript, and CSS for the stored flag values. Endpoint references are acceptable where endpoint discovery is intentional; literal flag exposure is not.

The exact Phase 37 checklist text is not present in the repository or workspace. The checklist below is therefore reconstructed under the four categories named in the request: application, CTF, teaching, and safety. It must not be represented as a verbatim copy of an unavailable blueprint.

Burp Suite's graphical interface was not automated in this environment. Test A reproduced the same HTTP requests, cookies, headers, redirects, JSON changes, and Repeater-style parameter changes with Flask's test client against an isolated database. A final manual classroom-device pass through Burp remains advisable.

## Automated Evidence

- Full v1.0 regression and release-audit suite: **24/24 passed**.
- Intended challenge workflows: **13/13 passed**.
- Retrieved values matching server-side challenge flags: **13/13**.
- Normal successful submissions: **13/13**.
- Total no-hint score: **3,050**, matching the challenge map.
- Active challenges: **13**.
- Unique flags: **13**.
- Flags using the `BLCTF{...}` format: **13/13**.
- Flag literals found in rendered challenge pages, templates, JavaScript, or CSS: **0**.
- Challenges 1–12 with three populated hints: **12/12**.
- Challenge 13 hint fields: **all `NULL`, as designed**.
- Authenticated HTML smoke routes returning `200`: **8/8**.
- Authenticated normal API smoke routes returning `200`: **4/4**.
- Anonymous protected HTML routes redirecting to login: **8/8**.
- Anonymous normal API access: **`401`**.
- Anonymous admin access: **`404`**.
- Valid logout invalidating subsequent protected access: **passed**.

## Three-perspective Results

### 1. First Request

- **Test A: PASS.** The normal lab request returns the matching flag only in `X-Lab-Flag`; submitting it succeeds.
- **Test B: PASS.** The hints progress from using Proxy, to inspecting the response, to checking nonstandard response headers.
- **Test C: PASS.** No flag is present in challenge HTML or client assets. The flag appears only in the intended runtime response header.

### 2. Read the Response

- **Test A: PASS.** Triggering the response reader produces background JSON whose undisplayed field matches and submits successfully.
- **Test B: PASS.** The hints identify the response reader, background JSON request, and comparison between raw JSON and rendered output.
- **Test C: PASS.** Neither the page nor `read-response.js` contains the flag. The runtime API response is the intended discovery location.

### 3. Repeater

- **Test A: PASS.** Replaying the starter lookup with permitted IDs 1–3 identifies the matching response header at ID 3.
- **Test B: PASS.** The hints explicitly establish Repeater, the permitted numeric range, and response-header inspection.
- **Test C: PASS.** The flag is absent from HTML and JavaScript and appears only in the altered request's response.

### 4. Change the Parameter

- **Test A: PASS.** Controlled testing of IDs 4–50 produced exactly one successful hidden record, ID 42, with the matching response header.
- **Test B: PASS.** The hints progressively identify the expanded range, the culturally familiar number, and the exact successful response to inspect.
- **Test C: PASS.** No client source contains the flag or literal answer. The runtime response is required.

### 5. Cookies

- **Test A: PASS.** The issued `blctf_lab_session` value was extracted, retained as a cookie, supplied to the check request, and accepted before flag submission.
- **Test B: PASS.** The hints identify `Set-Cookie`, the correct cookie name, and the required `session_value` use.
- **Test C: PASS.** The random token and flag are generated or loaded server-side and do not appear in page or asset source.

### 6. Headers

- **Test A: PASS.** The ordinary request has no flag; adding the intended debug request header changes the response and returns the matching flag.
- **Test B: PASS.** The hints identify that a header must be added, give its name, then give its exact value and inspection target.
- **Test C: PASS.** The flag is not embedded in client source and appears only after the modified runtime request.

### 7. Login Investigation

- **Test A: PASS.** A newly registered normal student completed login, and the successful intermediate redirect response exposed the matching challenge header.
- **Test B: PASS.** The hints direct the beginner to log out, capture the login cycle, inspect `POST /login`, and examine the successful `302` headers.
- **Test C: PASS.** Login and dashboard HTML contain no flag; the successful runtime redirect header is required.

### 8. Authorization

- **Test A: PASS.** Alice's fictional order 7001 contains no flag; changing the dedicated challenge-order ID to 7002 returns Bob's fictional `private_note`, which submits successfully.
- **Test B: PASS.** The hints identify the isolated route, starter ID, adjacent record, and returned field to inspect.
- **Test C: PASS.** The flag is absent from client source. It is returned only from the isolated challenge record endpoint.

### 9. API Discovery

- **Test A: PASS.** Dashboard activity exposes an unrendered authenticated API request in proxy-equivalent history, whose JSON token matches the challenge flag.
- **Test B: PASS.** The hints progress from dashboard reload, to filtering `/api/`, to inspecting the internal debug response.
- **Test C: PASS.** `dashboard-activity.js` contains the intended endpoint reference but no flag. The dashboard HTML does not render the value.

### 10. JSON Manipulation

- **Test A: PASS.** The normal fictional profile update has no reward; adding the intended unexpected boolean field returns the matching `lab_reward`.
- **Test B: PASS.** The hints distinguish the lab endpoint from the real profile API and provide the hidden field name, required type, and inspection step.
- **Test C: PASS.** The page and `json-manipulation.js` contain no flag. The modified runtime JSON request is necessary.

### 11. Hidden Endpoint

- **Test A: PASS.** Inspecting the challenge-specific JavaScript reveals the retired route; requesting it while authenticated returns the matching `archive_key`.
- **Test B: PASS.** The hints lead from asset inspection, to the legacy path reference, to directly requesting it.
- **Test C: PASS.** The JavaScript intentionally exposes the endpoint path but not the flag. The flag exists only in the endpoint response, so no redesign is indicated.

### 12. Multi-step Challenge

- **Test A: PASS.** Record 1 issues no token; changing to record 12 issues the challenge cookie, and presenting it to the second endpoint returns the matching flag.
- **Test B: PASS.** The hints establish the range and useful record, identify `Set-Cookie` and the next path, and state the final cookie placement.
- **Test C: PASS.** No flag or reusable token is embedded in source. The token is random, short-lived, and delivered only at runtime.

### 13. Final Challenge

- **Test A: PASS.** Proxy-equivalent background-traffic review found the capstone API. Its response header disclosed the optional parameter; each single change returned `404`, while combining the archived parameter with adjacent record 1302 returned the matching fictional private note.
- **Test B: N/A — intentional design exception.** Challenge 13 has no hint UI or stored hints by specification. Direct hint access returns `404` and does not create hint progress.
- **Test C: PASS.** The challenge HTML and `capstone-audit.js` contain neither the flag nor the required optional parameter. The script contains only the starting request, and the flag requires the runtime response plus two controlled changes.

## Phase 37 Checklist

### Application

- [x] **PASS — Application factory initializes successfully.** All test applications were created from a fresh seed.
- [x] **PASS — Default network binding is local-only.** Configuration defaults to `127.0.0.1`; LAN binding requires explicit `LAB_ALLOW_LAN=1`.
- [x] **PASS — Registration, login, session validation, CSRF-protected logout, and post-logout denial work.** A new fictional student was used in the end-to-end simulation.
- [x] **PASS — Protected HTML application pages work for authenticated students.** Dashboard, products, product detail, orders, profile, challenges, challenge detail, and scoreboard returned `200`.
- [x] **PASS — Normal JSON APIs work with authentication and reject anonymous access.** Products, product detail, profile, and orders returned `200` when authenticated; anonymous access returned `401`.
- [x] **PASS — Admin routes enforce the exact role server-side and hide navigation from other roles.** Covered by the regression suite.
- [x] **PASS — Reset is confirmation- and CSRF-protected, repeatable, and schema-safe.** Two consecutive resets passed integrity and foreign-key checks.
- [x] **PASS — Root README reflects the completed application.** QA-01 updated the stale description and added links to the student and instructor guides.

### CTF

- [x] **PASS — All 13 seeded challenges are active and individually solvable through their intended HTTP workflow.**
- [x] **PASS — All 13 flags are unique and use the `BLCTF{...}` format.**
- [x] **PASS — Retrieved flags validate through the normal submission endpoint.** Thirteen completions were recorded for the isolated QA student.
- [x] **PASS — No-hint scoring totals 3,050 points and matches the challenge map.**
- [x] **PASS — Duplicate scoring is prevented.** Existing regression coverage verifies a second correct submission does not add points.
- [x] **PASS — Flag comparison is server-side and constant-time.** `hmac.compare_digest` is used in the submission engine.
- [x] **PASS — Attempts and rapid repeated submissions are recorded or logged.** The engine persists attempt counts and emits the configured rapid-submission warning.
- [x] **PASS — Progressive hint use drives the 90%/75%/50% penalty.** Existing tests verify the persisted level and a two-hint 75% award.
- [x] **PASS — Flags are not trivially exposed in rendered HTML, templates, JavaScript, or CSS.** The exact stored flag set produced zero matches.
- [x] **PASS — Scoreboard output remains summary-only.** Existing routes expose username, rank, and score without flags, email, or hint detail.

### Teaching

- [x] **PASS — Challenge progression moves from basic proxy inspection through Repeater, cookies, headers, authorization, APIs, chaining, and a capstone.**
- [x] **PASS — Challenges 1–12 each provide three useful, progressively specific hints.** The final hint in each applicable challenge is sufficient to identify the decisive request or observation.
- [x] **PASS — Challenge 13 intentionally tests unaided synthesis.** Category and hint UI are absent as designed.
- [x] **PASS — Student documentation explains setup and general Burp concepts without concrete solutions or flags.**
- [x] **PASS — Instructor answer key contains objective, intended vulnerability, starting state, workflow, flag, common mistakes, and teaching notes for all 13 challenges.**
- [x] **PASS — Instructor challenge map matches 13 seeded IDs, titles, categories, difficulties, points, and the 3,050-point maximum.**
- [x] **PASS — Reset guidance covers timing, consequences, access controls, logging, verification, and recovery.**
- [x] **PASS — All top-level onboarding documentation is current.** The root README and student guide now describe the completed application and direct each audience to the appropriate documentation.

### Safety

- [x] **PASS — Seed data is clearly fictional.** Seeded emails use the reserved `.invalid` domain and records use fictional labels.
- [x] **PASS — The intentionally vulnerable application is local-only by default.**
- [x] **PASS — Challenge weaknesses are isolated to dedicated `/lab`, `/api/lab`, or challenge-order behavior and fictional tables.**
- [x] **PASS — Real order routes retain per-user ownership filtering.** Both HTML and API queries filter on the authenticated user ID; isolation tests pass.
- [x] **PASS — Real profile validation remains separate from the mass-assignment exercise.** Unexpected fields are rejected by `/api/profile`.
- [x] **PASS — Login sessions remain random, server-side, expiring, and revocable.** Challenge cookies and tokens do not replace authentication.
- [x] **PASS — Admin UI hiding is backed by exact-role server authorization.** Anonymous, student, and legacy instructor access returns `404`.
- [x] **PASS — Reset logs identify the event, actor ID, and UTC time without sensitive values.**
- [x] **PASS — Instructor documentation is not routed or referenced by application templates.** Source grep produced no `instructor/` references in `app/` or `templates/`.
- [x] **PASS — Client source contains no literal challenge flags.** Server-side seed data, instructor documentation, and tests are intentionally excluded from this browser-source criterion.

## Remediation Results

### QA-01 — Root README is stale

- **Severity:** Low
- **Status:** Resolved
- **Fix:** Replaced the obsolete minimal-landing-page statement with the current application capabilities and links to the student guide, challenge map, answer key, and reset guide.
- **Test A rerun:** PASS — the documented application factory initialized and the landing page returned `200`.
- **Test B rerun:** PASS — all three hints remain populated for Challenges 1–12, and Challenge 13 remains the intended no-hint exception.
- **Test C rerun:** PASS — no concrete flag literal appears in `README.md`, rendered templates, or static client assets.
- **Regression:** PASS — 21/21 automated tests passed after the documentation change.

## Items Not Requiring Redesign

- Challenge 11 intentionally exposes a route reference in JavaScript; Test C concerns flag disclosure, and no flag is present there.
- Challenges 2, 8–10, and 13 return flags in intended runtime JSON responses. Those responses are the challenge mechanism and are not embedded in page or asset source.
- Challenge 13's Test B is not a failure because the capstone's explicit design requires no hints.

## Final QA Disposition

**Challenge release status: PASS with no open findings from this report.** No challenge failed Test A or Test C, all applicable challenges passed Test B, and no challenge was flagged for vulnerability redesign. QA-01 is resolved. Exact Phase 37 parity remains unconfirmed until the original blueprint checklist text is supplied, but every item reconstructed under the requested application/CTF/teaching/safety categories is recorded above.

## v1.0 Release Verification

**Date:** 2026-09-02  
**Result:** PASS

- The operative 36-item Phase 37 application/CTF/teaching/safety checklist
  recorded above was rerun end to end: **36/36 passed**.
- The full regression and release-audit suite passed: **24/24 tests**.
- All intended discovery and submission workflows were rerun against a fresh,
  isolated seed: **13/13 passed**, with 13 completions and the expected
  no-hint total of 3,050 points.
- Beginner support and source-inspection checks passed: Challenges 1–12 retain
  three useful progressive hints, Challenge 13 remains the intentional no-hint
  exception, and no concrete seeded flag appears in browser-delivered template,
  JavaScript, or CSS source.
- A new client with no cookies or prior session state requested every registered
  route and supported application method: **40/40 route/method combinations
  swept**. Response bodies and headers contained no seeded challenge flag,
  administrator username, email, display name, password hash, known seeded
  administrator password, or instructor-document marker.
- Direct anonymous probes for `/instructor/`, each instructor Markdown
  document, and static path-traversal variants returned `404`. The URL map
  contains no instructor route or endpoint.
- Default native and containerized binding remains local-only. Classroom LAN
  exposure requires the documented explicit application and Docker publication
  opt-ins.

The original blueprint's verbatim Phase 37 text is still not stored in this
repository. This rerun therefore verifies the complete 36-item checklist
previously reconstructed and recorded in this report, without claiming textual
parity with an unavailable source.
