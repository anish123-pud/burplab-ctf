# BurpLab CTF Instructor Answer Key

This document consolidates the instructor solution for all seeded challenges. All accounts, products, orders, records, and flags are fictional and local to BurpLab. Intentional weaknesses are confined to challenge routes and datasets; normal account, profile, order, and session controls remain protected.

## Scoring and Instructor Access

Challenges 1–12 provide three progressively unlocked hints. The server awards 100% with no hint, 90% after hint 1, 75% after hint 2, or 50% after hint 3. Challenge 13 intentionally provides no hints. Correct resubmissions never award duplicate points.

The read-only dashboard and reset controls require the exact `admin` role. Seeded credentials are `admin01` / `admin-lab-only`. See [reset-guide.md](reset-guide.md) for reset procedures.

## 1. First Request

### Objective

Teach students to proxy a browser action and inspect the complete response, including metadata the browser does not render.

### Intended vulnerability

Information disclosure through a nonstandard response header on a dedicated challenge request.

### Starting state

The challenge page links to authenticated `GET /lab/first-request`. Its visible JSON contains only a status and fictional public message.

### Expected workflow

1. Send the training request through Burp Proxy.
2. Locate it in Proxy HTTP history.
3. Inspect response headers as well as the body.
4. Submit the `X-Lab-Flag` header value.

### Flag

`BLCTF{first_request}` — returned only in the `X-Lab-Flag` response header.

### Common mistakes

- Inspecting only the request.
- Reading the response body but overlooking headers.
- Submitting the header name instead of its value.

### Teaching notes

Establish the habit of treating headers and bodies as equally important evidence. The route requires login and contains no real application data.

## 2. Read the Response

### Objective

Demonstrate that a browser interface may display only part of an HTTP response.

### Intended vulnerability

Sensitive-field exposure in an API response consumed by JavaScript but omitted from the rendered page.

### Starting state

The **Load response** button requests `GET /lab/read-response/data`. JavaScript renders only the public `message` field.

### Expected workflow

1. Select **Load response** while HTTP history is recording.
2. Locate the background JSON request.
3. Compare the complete response with the single value shown in the UI.
4. Submit the undisplayed `internal_note` value.

### Flag

`BLCTF{read_the_response}` — the `internal_note` JSON property.

### Common mistakes

- Searching the main HTML source.
- Trusting the rendered message as the complete response.
- Inspecting JavaScript without inspecting its network response.

### Teaching notes

Use this exercise to distinguish source inspection, DOM rendering, and actual HTTP response content.

## 3. Repeater

### Objective

Teach capture-to-Repeater workflow and controlled modification of one query parameter.

### Intended vulnerability

A challenge response discloses metadata for one alternate permitted fictional product ID.

### Starting state

The starter request is `GET /product?id=1`. Challenge 3 limits students to the normal lab set 1–3.

### Expected workflow

1. Capture the starter request and send it to Repeater.
2. Test `id=1`, `id=2`, and `id=3` one at a time.
3. Compare complete responses.
4. Read the special response header for product 3.

### Flag

`BLCTF{repeater_product_3}` — the `X-Lab-Flag` header for `GET /product?id=3`.

### Common mistakes

- Editing only the browser address bar.
- Trying values outside the stated exercise range.
- Comparing bodies while ignoring headers.

### Teaching notes

Emphasize repeatability and changing one variable at a time. This route uses isolated `lab_products`, not the normal product-detail route.

## 4. Change the Parameter

### Objective

Show how a client-controlled parameter can select an unexpected but bounded record.

### Intended vulnerability

Unintended record discovery through direct numeric query-parameter manipulation.

### Starting state

The starter is `GET /product?id=1`. IDs 1–3 are obvious; exactly one extra seeded `lab_products` record exists within 1–50.

### Expected workflow

1. Send the starter to Repeater.
2. Vary only `id` within the permitted range.
3. Identify the successful hidden record at `id=42`.
4. Inspect its complete response and submit the special header value.

### Flag

`BLCTF{parameter_42}` — the `X-Lab-Flag` header for `GET /product?id=42`.

### Common mistakes

- Using `/product/<id>`, the protected normal product route.
- Sending IDs outside the bounded range.
- Missing the flag because the JSON body looks ordinary.

### Teaching notes

Discuss bounded enumeration and authorization. All other unused IDs return `404`, and the dataset is entirely fictional.

## 5. Cookies

### Objective

Teach students to identify, inspect, and reuse a challenge cookie without weakening the real login session.

### Intended vulnerability

Challenge authorization depends on replaying a client-held cookie value through a related request parameter.

### Starting state

`GET /lab/cookies/start` issues random `blctf_lab_session` and identifies a verification path. The server stores only a user-bound digest.

### Expected workflow

1. Issue the challenge cookie.
2. Copy its value from `Set-Cookie`.
3. Send the related check request to Repeater.
4. Replace its placeholder with the exact value while retaining login and challenge cookies.
5. Inspect the verified response headers.

### Flag

`BLCTF{cookie_session_marker}` — `X-Lab-Flag` after successful validation.

### Common mistakes

- Copying the Flask login cookie.
- Omitting the challenge cookie while supplying its value as a parameter.
- Issuing a new token and replaying the invalidated old one.

### Teaching notes

Contrast this exercise cookie with the real opaque login session. Tokens are random, short-lived, and user-bound.

## 6. Headers

### Objective

Teach students to add a request header in Repeater and analyze a conditional response.

### Intended vulnerability

A challenge-only debug mode is activated by a client-controlled custom header.

### Starting state

`GET /lab/headers` returns standard fictional diagnostics without debug metadata.

### Expected workflow

1. Capture the request and send it to Repeater.
2. Add `X-Lab-Debug: enabled`.
3. Resend and compare the body and headers.
4. Submit the new response-header value.

### Flag

`BLCTF{custom_debug_header}` — `X-Lab-Flag` when the exact debug header is present.

### Common mistakes

- Adding the header to a response rather than the request.
- Using `true`, `1`, or another value instead of `enabled`.
- Seeing changed JSON but overlooking headers.

### Teaching notes

Reinforce exact header syntax and application values. The behavior exists only on `/lab/headers`.

## 7. Login Investigation

### Objective

Teach inspection of a complete login exchange, especially an intermediate redirect response.

### Intended vulnerability

Challenge information is exposed on a successful login redirect but not on failures or the final dashboard.

### Starting state

A valid login produces `POST /login`, a `302`, and a subsequent dashboard request that the browser follows immediately.

### Expected workflow

1. Log out and start a clean HTTP-history capture.
2. Log in with valid fictional credentials.
3. Inspect the successful `POST /login` response before its redirect.
4. Submit the `X-Lab-Login-Note` value.

### Flag

`BLCTF{login_response_cycle}` — the `X-Lab-Login-Note` header on the successful login response.

### Common mistakes

- Inspecting only submitted credentials.
- Looking only at the dashboard response.
- Testing invalid credentials, whose response has no challenge header.

### Teaching notes

Use the sequence to explain redirects and why proxy history preserves intermediate traffic better than the browser view.

## 8. Authorization

### Objective

Demonstrate an IDOR without exposing real students' orders.

### Intended vulnerability

The dedicated challenge-order route accepts a changed object ID but omits ownership enforcement.

### Starting state

The lab assumes fictional Alice and links to `/challenge-orders/7001`. Bob's adjacent fictional order is `7002`, stored only in `lab_order_accounts` and `lab_orders`.

### Expected workflow

1. Capture Alice's starter order and send it to Repeater.
2. Change the path ID from `7001` to `7002`.
3. Observe that the route returns Bob's record despite the Alice identity.
4. Submit Bob's `private_note`.

### Flag

`BLCTF{idor_bobs_order}` — `private_note` from `GET /challenge-orders/7002`.

### Common mistakes

- Testing real `/orders` or `/api/orders`, which enforce ownership.
- Changing a real user ID rather than the fictional order ID.
- Overlooking `private_note`.

### Teaching notes

Authentication does not provide object-level authorization automatically. The IDOR is isolated; real orders remain filtered by logged-in user ID.

## 9. API Discovery

### Objective

Teach discovery of authenticated background API traffic with no visible navigation or output.

### Intended vulnerability

An undocumented internal endpoint returns challenge information to any authenticated user.

### Starting state

The dashboard silently requests `GET /api/internal/debug` through `dashboard-activity.js` and never renders its response.

### Expected workflow

1. Reload the dashboard while recording HTTP history.
2. Locate the background `/api/` request.
3. Inspect its complete JSON response.
4. Submit the `debug_token` value.

### Flag

`BLCTF{undocumented_debug_api}` — `debug_token` from `GET /api/internal/debug`.

### Common mistakes

- Searching only visible links.
- Looking only at HTML document requests.
- Replaying the API without authentication.

### Teaching notes

Show how passive HTTP-history review reveals application surface area even without useful DOM output.

## 10. JSON Manipulation

### Objective

Demonstrate mass-assignment-style behavior through an unexpected JSON property.

### Intended vulnerability

A fictional profile endpoint updates a transient object with unrecognized input, allowing a hidden boolean property to be set.

### Starting state

The challenge sends `POST /api/lab/profile` with fictional `display_name` and `theme`; its ordinary response contains no reward.

### Expected workflow

1. Capture the fictional profile update and send it to Repeater.
2. Add JSON boolean `"lab_access": true`.
3. Preserve valid JSON and resend.
4. Submit the returned `lab_reward`.

### Flag

`BLCTF{unexpected_json_field}` — `lab_reward` when `lab_access` is boolean `true`.

### Common mistakes

- Sending the field to real `/api/profile`, which rejects it.
- Sending string `"true"` instead of boolean `true`.
- Looking only at the page's status message.

### Teaching notes

The permissive assignment touches only a transient dictionary. Contrast it with the real profile's strict allowlist.

## 11. Hidden Endpoint

### Objective

Teach methodical endpoint discovery through supporting assets.

### Intended vulnerability

A retired authenticated route remains referenced in JavaScript despite having no link or automatic request.

### Starting state

The page loads `static/js/legacy-lab-reference.js`, which retains a path but does not call or display it.

### Expected workflow

1. Inspect JavaScript assets loaded by the page.
2. Find `/lab/archive/retired-status` in the legacy file.
3. Request the path directly while authenticated.
4. Submit the JSON `archive_key`.

### Flag

`BLCTF{hidden_route_found}` — `archive_key` from the retired-status endpoint.

### Common mistakes

- Inspecting only visible anchors.
- Waiting for the endpoint to appear automatically.
- Requesting the JavaScript file instead of its referenced path.

### Teaching notes

Discuss why unused routes and stale client references increase attack surface. This endpoint reads only Challenge 11 metadata.

## 12. Multi-step Challenge

### Objective

Require a chain of proxy capture, parameter modification, cookie inspection, and authenticated follow-up.

### Intended vulnerability

A specific fictional record issues a challenge token that authorizes a second endpoint when replayed as a cookie.

### Starting state

The starter is `GET /lab/chain/start?record=1`. IDs 1–20 are accepted; record 12 issues random `blctf_chain_token` and identifies `/lab/chain/finish`.

### Expected workflow

1. Send the starter to Repeater and change `record` to `12`.
2. Copy the token from `Set-Cookie`.
3. Request `GET /lab/chain/finish` with both normal login and challenge cookies.
4. Submit the returned `flag`.

### Flag

`BLCTF{chained_request_token}` — returned after validating the user-bound ten-minute token.

### Common mistakes

- Guessing rather than extracting the token.
- Omitting the normal login session.
- Sending the token as a query parameter.
- Reusing an expired or superseded token.

### Teaching notes

Map each artifact to its role in the chain. Token digests live only in `lab_chain_tokens`; real sessions, profiles, and orders are unchanged.

## 13. Final Challenge

### Objective

Assess independent recognition and chaining of earlier techniques without a category or hints.

### Intended vulnerability

An undocumented query parameter activates an archived-record branch whose dedicated fictional authorization query omits its owner condition. Discovery combines background API inspection, response-header analysis, and ID manipulation.

### Starting state

The student sees only:

> A flag has been hidden somewhere in this application. You have a normal student account and Burp Suite. Find it.

The UI omits category, application instructions, and hints. Loading `/challenge/13` silently runs `capstone-audit.js`, which requests:

```http
GET /api/lab/capstone/audit?record=1301 HTTP/1.1
Cookie: session=<valid normal student session>
Accept: application/json
```

The response identifies assumed fictional Alice and active record 1301, and includes:

```http
X-Lab-Optional-Query: include_archived=true
```

The isolated data contains active Alice record 1301 and archived Bob record 1302. Only IDs 1300–1310 are accepted.

### Expected workflow

1. Clear HTTP history and open the final challenge.
2. Review all generated traffic, including JavaScript and fetch/XHR requests.
3. Locate `GET /api/lab/capstone/audit?record=1301` directly or through `capstone-audit.js`.
4. Inspect its response. Note Alice, record 1301, active state, and `X-Lab-Optional-Query`.
5. Send the authenticated request to Repeater.
6. Add `include_archived=true` to record 1301. It returns `404`, showing archived mode selects another record set.
7. Try record 1302 without the parameter. The default owner check also returns `404`.
8. Combine both changes:

   ```http
   GET /api/lab/capstone/audit?record=1302&include_archived=true HTTP/1.1
   Cookie: session=<valid normal student session>
   Accept: application/json
   ```

9. Observe that assumed Alice receives archived Bob's record. Submit `record.private_note`.

The default query enforces `id = ? AND fictional_owner = 'alice' AND archived = 0`; archived mode intentionally changes it to `id = ? AND archived = 1`. Neither individual change reveals the flag.

### Flag

`BLCTF{capstone_audit_bypass}` — `private_note` on fictional Bob record 1302 when both query changes are present.

### Common mistakes

- Looking only at rendered content.
- Inspecting requests without checking response headers.
- Changing only `record`, or adding only `include_archived=true`.
- Using `1`, `True`, or `yes`; only lowercase `true` activates archived mode.
- Dropping the authenticated session in Repeater.
- Testing real profile or order routes.

### Teaching notes

Ask process questions if a student stalls: what traffic did the page generate, what did the complete response disclose, and what assumptions can be tested separately? Do not reveal the parameter or record ID as a hint; the capstone intentionally has no hint endpoint.

The flaw is confined to `/api/lab/capstone/audit` and `lab_final_records`, which has no relationship to real users, sessions, profiles, or orders. Verify that the initial response contains no flag, each single-change request returns `404`, the combined request returns Bob's fictional record, anonymous access returns `401`, and correct submission awards 500 points once.
