# BurpLab CTF Student Guide

BurpLab CTF is a local web-security training application for learning Burp Suite in a controlled environment. The application is intentionally vulnerable in challenge-specific areas and contains fictional data only.

Use BurpLab only on the local lab instance provided by your instructor. Do not apply these exercises to real systems or to any target without explicit authorization.

## Prerequisites

- Python 3
- Burp Suite Community Edition or Professional
- A modern web browser
- A local copy of the BurpLab CTF project

## Start BurpLab

From the `burplab-ctf` project directory, create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies and initialize the fictional database if your instructor has not already done so:

```bash
python -m pip install -r requirements.txt
python scripts/init_db.py
```

Start the application:

```bash
python run.py
```

Open <http://127.0.0.1:5000>. BurpLab binds to the local machine by default. Leave the terminal running while completing the exercises.

## Configure Burp Proxy

The simplest setup uses Burp's built-in browser:

1. Open Burp Suite and create or open a temporary project.
2. Go to **Proxy → Intercept**.
3. Select **Open browser**.
4. In the Burp browser, visit <http://127.0.0.1:5000>.
5. Set **Intercept is off** during normal browsing unless a challenge asks you to pause a request. Burp continues recording traffic in **Proxy → HTTP history**.

If you use an external browser, configure its HTTP proxy as `127.0.0.1` on port `8080`, matching Burp's default proxy listener. The lab uses plain local HTTP, so a Burp CA certificate is not required for the default setup.

Keep the Burp target scope limited to `127.0.0.1:5000`. This makes HTTP history easier to read and avoids capturing unrelated browsing traffic.

## Create an Account and Start

1. Open BurpLab through the proxied browser.
2. Register a normal student account using fictional details only, or use credentials supplied by your instructor.
3. Log in and open **Challenges** from the navigation bar.
4. Select a challenge and read its description carefully.
5. Complete the application interaction described on the challenge page.
6. Submit discovered flags through the challenge's **Submit Flag** form.

Flags use the format `BLCTF{...}`. Do not share flags or solution steps with other students during an assessed session.

## Core Burp Concepts

### Proxy and HTTP history

Burp Proxy sits between the browser and the local application. HTTP history records requests and responses even when interception is off. Use it to identify document requests, background API traffic, redirects, headers, cookies, and response bodies.

### Requests and responses

An HTTP request includes a method, path, parameters, headers, cookies, and sometimes a body. The response includes a status code, headers, and a body. The browser may render only part of the returned information, so inspect the complete exchange.

### Repeater

Repeater lets you resend one captured request while changing controlled details. Right-click a request and choose **Send to Repeater**, then adjust one item at a time. Comparing responses is often more useful than making many unrelated changes.

### Parameters

Parameters may appear in the URL query string, path, form body, or JSON body. They are controlled by the client and can affect which action or record the server selects. Stay within the fictional ranges stated by each challenge.

### Headers

Headers carry request and response metadata. Examples include content types, redirect locations, caching instructions, and application-specific headers. Review both standard and nonstandard headers.

### Cookies and sessions

Cookies are sent in request headers and created or updated through response headers. Some identify an authenticated session; others may belong only to a specific exercise. Preserve your normal login session when moving authenticated requests into Repeater.

### JSON and APIs

API traffic often uses JSON rather than HTML. Check the request method and `Content-Type`, preserve valid JSON syntax, and inspect every returned field. Background requests may not produce any visible page update.

### Status codes and redirects

Status codes are evidence. A redirect, authorization failure, missing record, validation failure, and successful response indicate different application decisions. Burp can show intermediate responses that the browser follows too quickly to display.

## A Productive Challenge Workflow

1. Read the challenge description and any application instructions.
2. Clear or mark Burp's HTTP history before beginning.
3. Perform the normal action once in the browser.
4. Identify the relevant request and inspect its complete response.
5. Send the request to Repeater when controlled modification is appropriate.
6. Change one value at a time and compare status codes, headers, and bodies.
7. Keep authentication cookies and required request formatting intact.
8. Use the progressive in-app hints if needed. Revealed hints reduce the available score.
9. Submit only complete `BLCTF{...}` values in the flag form.

## Troubleshooting

- If the site does not load, confirm `python run.py` is still running and use `http://127.0.0.1:5000`.
- If Burp shows no traffic, use Burp's built-in browser or verify the external browser proxy settings.
- If a Repeater request redirects to login or returns an authentication error, recapture it after logging in and retain the current session cookie.
- If a POST fails with a CSRF error, begin again from the current page and use its latest form token.
- If the database or accounts have been reset, log in again. Ask the instructor before recreating the database yourself during a class.
- If a challenge response seems unchanged, compare the complete request and response rather than only the rendered browser page.

## Lab Boundaries

Challenge behavior is intentionally scoped to dedicated fictional records and routes. The normal profile and order features are not permission to access another person's information. Stop and ask the instructor if an exercise appears to require leaving `127.0.0.1:5000`, using real data, or targeting another system.
