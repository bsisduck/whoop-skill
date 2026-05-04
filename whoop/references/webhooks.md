# WHOOP Webhooks v2

## Table of Contents
- [Setup](#setup)
- [Event Types](#event-types)
- [Payload Schema](#payload-schema)
- [Signature Verification](#signature-verification)
- [Retry Policy](#retry-policy)
- [Flask Example](#flask-example)
- [Express Example](#express-example)

## Setup

1. Create an HTTPS endpoint that accepts POST requests
2. In WHOOP Developer Dashboard, add webhook URL and select **v2** model version
3. Each app gets one webhook URL
4. Webhook fires when any authorized user's data changes

## Event Types

| Event | Trigger |
|-------|---------|
| `workout.updated` | Workout created or modified |
| `workout.deleted` | Workout removed |
| `sleep.updated` | Sleep created or modified |
| `sleep.deleted` | Sleep removed |
| `recovery.updated` | Recovery created or modified |
| `recovery.deleted` | Recovery removed |

Note: Recovery events use the associated **sleep UUID** as `id`, not a cycle ID.

## Payload Schema

```json
{
  "user_id": 456,
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "sleep.updated",
  "trace_id": "e369c784-5100-49e8-8098-75d35c47b31b"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | int64 | WHOOP user ID |
| `id` | UUID | Resource ID (sleep UUID for recovery events) |
| `type` | string | Event type from table above |
| `trace_id` | string | Unique event ID for deduplication |

Webhooks are **notifications only** — call the API with the UUID to get full data.

## Signature Verification

WHOOP signs every webhook with HMAC-SHA256 using your client secret.

**Headers sent:**
- `X-WHOOP-Signature`: Base64-encoded HMAC-SHA256 signature
- `X-WHOOP-Signature-Timestamp`: Milliseconds since epoch

**Verification algorithm:**
```
message = timestamp_header + raw_request_body
calculated = base64_encode(HMAC_SHA256(message, client_secret))
valid = constant_time_compare(calculated, signature_header)
```

Always use constant-time comparison to prevent timing attacks.

## Retry Policy

- WHOOP retries failed deliveries **5 times over ~1 hour**
- Failed = non-2XX response or timeout
- Return 2XX within 1 second
- Process data asynchronously after acknowledging

## Flask Example

```python
import base64
import hashlib
import hmac
import json
from flask import Flask, request, abort

app = Flask(__name__)
CLIENT_SECRET = "your_client_secret"

def verify_signature(payload, timestamp, signature):
    message = timestamp.encode() + payload
    expected = base64.b64encode(
        hmac.new(CLIENT_SECRET.encode(), message, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(expected, signature)

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-WHOOP-Signature")
    timestamp = request.headers.get("X-WHOOP-Signature-Timestamp")
    if not signature or not timestamp:
        abort(401)
    if not verify_signature(request.get_data(), timestamp, signature):
        abort(401)

    event = request.get_json()
    event_type = event["type"]
    resource_id = event["id"]
    user_id = event["user_id"]
    # Queue async processing here
    return "", 200
```

## Express Example

```javascript
const crypto = require("crypto");
const express = require("express");
const app = express();

const CLIENT_SECRET = "your_client_secret";

app.use("/webhook", express.raw({ type: "application/json" }));

function verifySignature(payload, timestamp, signature) {
  const message = Buffer.concat([Buffer.from(timestamp), payload]);
  const expected = crypto
    .createHmac("sha256", CLIENT_SECRET)
    .update(message)
    .digest("base64");
  const a = Buffer.from(expected);
  const b = Buffer.from(signature);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

app.post("/webhook", (req, res) => {
  const signature = req.headers["x-whoop-signature"];
  const timestamp = req.headers["x-whoop-signature-timestamp"];
  if (!signature || !timestamp || !verifySignature(req.body, timestamp, signature)) {
    return res.sendStatus(401);
  }
  const event = JSON.parse(req.body);
  // Queue async processing here
  res.sendStatus(200);
});
```
