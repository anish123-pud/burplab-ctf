-- All records below are invented solely for the local BurpLab training lab.
-- The .invalid top-level domain is reserved and cannot represent real accounts.

INSERT INTO users (id, username, password_hash, email, display_name, role, created_at) VALUES
    (1, 'student01', 'pbkdf2:sha256:600000$QyfKFu4l0bLW0uhw$5be9b6cd87547957b6babd3e18b2fb9758f86f13f092dfec62bb84ffed9bb1ef', 'student01@burplab.invalid', 'Student Zero One', 'student', '2026-01-10 09:00:00'),
    (2, 'student02', 'pbkdf2:sha256:600000$QyfKFu4l0bLW0uhw$5be9b6cd87547957b6babd3e18b2fb9758f86f13f092dfec62bb84ffed9bb1ef', 'student02@burplab.invalid', 'Student Zero Two', 'student', '2026-01-10 09:05:00'),
    (3, 'instructor01', 'pbkdf2:sha256:600000$U9m8CfOystmLIUNf$844981754e0d8734ba1de39318254fd747d3220ab610cb149c60a5261a090aa0', 'instructor01@burplab.invalid', 'Instructor Zero One', 'instructor', '2026-01-10 08:30:00'),
    (4, 'admin01', 'pbkdf2:sha256:600000$YzYUQHxKoFGcMsY0$5c1a03adb4b1ccaff54fd4e311ea2f4da678c6eb82e36dab79b8e8911295a0f9', 'admin01@burplab.invalid', 'Lab Administrator', 'admin', '2026-01-10 08:00:00');

INSERT INTO products (id, name, description, price, stock, created_at) VALUES
    (1, 'Proxy Practice Widget', 'A fictional widget used in local request exercises.', 19.99, 25, '2026-01-11 10:00:00'),
    (2, 'Request Replay Kit', 'An imaginary kit for the training storefront.', 34.50, 12, '2026-01-11 10:05:00'),
    (3, 'Sandbox Token Pack', 'A made-up token pack with no real-world value.', 7.25, 100, '2026-01-11 10:10:00');

INSERT INTO lab_products (id, name, price, stock) VALUES
    (1, 'Lab Widget One', 11.00, 10),
    (2, 'Lab Widget Two', 12.00, 20),
    (3, 'Lab Widget Three', 13.00, 30),
    (42, 'Out-of-Range Lab Widget', 42.00, 1);

INSERT INTO lab_order_accounts (id, username) VALUES
    (1, 'alice'),
    (2, 'bob');

INSERT INTO lab_orders (id, account_id, item_name, total_amount, private_note) VALUES
    (7001, 1, 'Alice Fictional Training Widget', 21.00, 'No private note for this fictional order.'),
    (7002, 2, 'Bob Fictional Training Gadget', 34.00, 'BLCTF{idor_bobs_order}');

INSERT INTO lab_final_records (
    id, fictional_owner, archived, public_note, private_note
) VALUES
    (1301, 'alice', 0, 'Routine fictional audit record.', 'No private note for this record.'),
    (1302, 'bob', 1, 'Archived fictional audit record.', 'BLCTF{capstone_audit_bypass}');

INSERT INTO orders (id, user_id, status, total_amount, created_at) VALUES
    (1, 1, 'paid', 34.49, '2026-01-12 14:00:00'),
    (2, 2, 'pending', 34.50, '2026-01-12 14:15:00');

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 1, 19.99),
    (2, 1, 3, 2, 7.25),
    (3, 2, 2, 1, 34.50);

INSERT INTO sessions (id, user_id, token, created_at, expires_at) VALUES
    -- This digest represents an expired fictional fixture, not a usable session.
    (1, 1, '6defb76051b01fd369dbe79e36c1a47bd3b8ac8d91c2ebb63024079f17e42a63', '2026-01-12 13:55:00', '2026-01-12 15:55:00');

INSERT INTO challenges (
    id, title, description, difficulty, category, points,
    flag, hint_1, hint_2, hint_3, active
) VALUES
    (
        1,
        'First Request',
        'Send your first training request through Burp Proxy and inspect the complete HTTP response. The browser page shows only the public result, so review the intercepted response metadata carefully.',
        'beginner',
        'proxy',
        100,
        'BLCTF{first_request}',
        'Open the lab request while your browser is using Burp Proxy.',
        'Inspect the response as well as the request.',
        'Pay attention to non-standard response headers.',
        1
    ),
    (
        2,
        'Read the Response',
        'Trigger the response reader, then inspect its raw HTTP response. The page deliberately renders only the public message and leaves other response data undisplayed.',
        'beginner',
        'response',
        125,
        'BLCTF{read_the_response}',
        'Use the response reader on this challenge page while Burp is capturing traffic.',
        'Find the background JSON request made by the page.',
        'Compare the raw JSON fields with the single message shown in the browser.',
        1
    ),
    (
        3,
        'Repeater',
        'Capture the starter product lookup and send it to Burp Repeater. Try only the permitted fictional product IDs 1 through 3 and inspect each complete response.',
        'beginner',
        'repeater',
        150,
        'BLCTF{repeater_product_3}',
        'Send the starter lookup to Repeater instead of editing the address bar.',
        'Change only the numeric id parameter and stay within 1 through 3.',
        'Inspect the headers on every successful response.',
        1
    ),
    (
        4,
        'Change the Parameter',
        'Capture the starter product request and change its client-controlled id parameter. Stay within the fictional lab range 1 through 50 and look for a seeded record outside the normal 1 through 3 set.',
        'beginner',
        'parameters',
        175,
        'BLCTF{parameter_42}',
        'The server accepts a bounded range larger than the three normal lab product IDs.',
        'Try a culturally familiar number between 4 and 50.',
        'Inspect the full successful response for id 42.',
        1
    ),
    (
        5,
        'Cookies',
        'Issue a challenge-scoped session cookie, inspect its random value in Burp, and use that exact value with the related verification request. The real login session remains server-validated and unchanged.',
        'beginner',
        'cookies',
        175,
        'BLCTF{cookie_session_marker}',
        'Start by issuing the challenge cookie and inspecting the Set-Cookie response header.',
        'Copy only the blctf_lab_session cookie value.',
        'Supply that value as session_value on the related check request.',
        1
    ),
    (
        6,
        'Headers',
        'Send the starter request to Repeater and observe how its response changes when the challenge-specific X-Lab-Debug header is enabled.',
        'beginner',
        'headers',
        200,
        'BLCTF{custom_debug_header}',
        'Add a custom request header in Repeater rather than changing the URL.',
        'The header name is X-Lab-Debug.',
        'Set X-Lab-Debug to enabled and inspect the complete response.',
        1
    ),
    (
        7,
        'Login Investigation',
        'Capture a complete successful login cycle in Burp, including the redirect response that follows the credential POST. A challenge-only response detail is not rendered by the browser.',
        'beginner',
        'authentication',
        225,
        'BLCTF{login_response_cycle}',
        'Log out, enable Proxy HTTP history, and log in again with your fictional lab account.',
        'Inspect the response to POST /login before following its redirect.',
        'Look through the successful 302 response headers.',
        1
    ),
    (
        8,
        'Authorization',
        'The challenge lab treats you as fictional user alice. Capture alice''s namespaced order request, change only its nearby numeric order ID, and determine whether another fictional account''s record is improperly returned.',
        'intermediate',
        'authorization',
        250,
        'BLCTF{idor_bobs_order}',
        'This challenge uses /challenge-orders/ routes, never the real /orders page.',
        'Alice''s starter order is 7001; try the next nearby fictional order ID.',
        'Inspect every field returned for bob''s fictional order.',
        1
    ),
    (
        9,
        'API Discovery',
        'Browse the dashboard with Burp recording HTTP history and look for an authenticated background API request that has no visible navigation link or rendered output.',
        'intermediate',
        'api',
        250,
        'BLCTF{undocumented_debug_api}',
        'Reload the dashboard while Proxy HTTP history is recording.',
        'Filter the captured requests to paths beginning with /api/.',
        'Inspect the complete JSON response from the internal debug request.',
        1
    ),
    (
        10,
        'JSON Manipulation',
        'Capture the fictional lab profile update and send it to Repeater. Add an unexpected JSON property that changes the lab-only profile state, then inspect the complete JSON response.',
        'intermediate',
        'api',
        275,
        'BLCTF{unexpected_json_field}',
        'This exercise uses /api/lab/profile, not the real /api/profile endpoint.',
        'The fictional profile has a normally hidden boolean property named lab_access.',
        'Add "lab_access": true to the JSON object and inspect the response.',
        1
    ),
    (
        11,
        'Hidden Endpoint',
        'A retired lab service is not linked or requested by the page. Methodically inspect the challenge page assets to discover its route, request it directly, and review the JSON response.',
        'intermediate',
        'discovery',
        275,
        'BLCTF{hidden_route_found}',
        'Inspect every JavaScript asset loaded by this challenge page.',
        'One challenge-specific script retains a legacy path reference.',
        'Request the referenced retired status path directly while authenticated.',
        1
    ),
    (
        12,
        'Multi-step Challenge',
        'Chain several observations: capture the starter record request, modify its record parameter in Repeater, extract the challenge cookie from the interesting response, and use it when requesting the supplied second endpoint.',
        'advanced',
        'chaining',
        350,
        'BLCTF{chained_request_token}',
        'The accepted fictional record range is 1 through 20; the useful record matches this challenge number.',
        'Record 12 returns a Set-Cookie header and identifies the next path.',
        'Send the blctf_chain_token cookie with GET /lab/chain/finish.',
        1
    ),
    (
        13,
        'Final Challenge',
        'A flag has been hidden somewhere in this application. You have a normal student account and Burp Suite. Find it.',
        'advanced',
        'mystery',
        500,
        'BLCTF{capstone_audit_bypass}',
        NULL,
        NULL,
        NULL,
        1
    );
