# WHOOP API v2 Reference

## Table of Contents
- [Base URL & Auth](#base-url--auth)
- [Rate Limits](#rate-limits)
- [Pagination](#pagination)
- [Endpoints: User](#user)
- [Endpoints: Cycle](#cycle)
- [Endpoints: Sleep](#sleep)
- [Endpoints: Recovery](#recovery)
- [Endpoints: Workout](#workout)
- [Endpoints: Activity Mapping](#activity-mapping)
- [Data Models](#data-models)
- [Sport Types](#sport-types)
- [Score States](#score-states)

## Base URL & Auth

```
Base: https://api.prod.whoop.com/developer
Auth: Bearer token in Authorization header
OAuth2 Authorization: https://api.prod.whoop.com/oauth/oauth2/auth
OAuth2 Token: https://api.prod.whoop.com/oauth/oauth2/token
```

### Scopes

| Scope | Access |
|-------|--------|
| `read:profile` | Name, email, user ID |
| `read:body_measurement` | Height, weight, max HR |
| `read:cycles` | Cycle data (strain, average heart rate) |
| `read:recovery` | Recovery score, HRV, resting heart rate |
| `read:sleep` | Sleep performance, duration per stage |
| `read:workout` | Workout strain, average heart rate |
| `offline` | Refresh token for long-lived access |

## Rate Limits

- **100 requests/minute**, **10,000 requests/day**
- Headers follow IETF draft spec:
  - `X-RateLimit-Limit`: e.g. `"100, 100;window=60, 10000;window=86400"`
  - `X-RateLimit-Remaining`: e.g. `"98"`
  - `X-RateLimit-Reset`: seconds until reset, e.g. `"3"`
- Exceeded: `429 Too Many Requests`
- Request increases via WHOOP support form

## Pagination

Collection endpoints return paginated results:

```json
{
  "records": [...],
  "next_token": "eyJhb..."
}
```

- Pass `nextToken` query param to get next page
- Empty `next_token` = last page
- `limit` param controls page size (max 25, default 10)
- `end` defaults to current time when omitted
- Always include original `start`/`end` params when paginating

---

## User

### GET /v2/user/profile/basic
**Scope:** `read:profile`

```json
{
  "user_id": 12345,
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Doe"
}
```

### GET /v2/user/measurement/body
**Scope:** `read:body_measurement`

```json
{
  "height_meter": 1.75,
  "weight_kilogram": 70.5,
  "max_heart_rate": 195
}
```

### DELETE /v2/user/access
Revoke OAuth access. Returns `204 No Content`. Stops webhook delivery for this user.

---

## Cycle

A Cycle = one physiological day (sleep-to-sleep, not midnight-to-midnight).

### GET /v2/cycle/{cycleId}
**Scope:** `read:cycles` | **Param:** `cycleId` (int64)

### GET /v2/cycle
**Scope:** `read:cycles` | **Paginated**

| Param | Type | Default | Max |
|-------|------|---------|-----|
| `limit` | int | 10 | 25 |
| `start` | ISO datetime | - | - |
| `end` | ISO datetime | now | - |
| `nextToken` | string | - | - |

### GET /v2/cycle/{cycleId}/sleep
Get sleep record for a specific cycle.

### GET /v2/cycle/{cycleId}/recovery
**Scope:** `read:recovery` — Get recovery for a specific cycle.

### Cycle Response

```json
{
  "id": 12345678,
  "user_id": 12345,
  "created_at": "2024-01-15T08:00:00.000Z",
  "updated_at": "2024-01-15T22:00:00.000Z",
  "start": "2024-01-15T07:30:00.000Z",
  "end": "2024-01-16T07:15:00.000Z",
  "timezone_offset": "+01:00",
  "score_state": "SCORED",
  "score": {
    "strain": 12.4532,
    "kilojoule": 2450.3,
    "average_heart_rate": 72,
    "max_heart_rate": 178
  }
}
```

**Notes:**
- `end` is **null** when the cycle is still active (current day)
- `score` is only present when `score_state` is `SCORED`

---

## Sleep

### GET /v2/activity/sleep/{sleepId}
**Scope:** `read:sleep` | **Param:** `sleepId` (UUID string)

### GET /v2/activity/sleep
**Scope:** `read:sleep` | **Paginated** (same params as Cycle)

### Sleep Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "cycle_id": 12345678,
  "v1_id": null,
  "user_id": 12345,
  "created_at": "2024-01-15T23:00:00.000Z",
  "updated_at": "2024-01-16T07:00:00.000Z",
  "start": "2024-01-15T23:00:00.000Z",
  "end": "2024-01-16T07:00:00.000Z",
  "timezone_offset": "+01:00",
  "nap": false,
  "score_state": "SCORED",
  "score": {
    "stage_summary": {
      "total_in_bed_time_milli": 28800000,
      "total_awake_time_milli": 2400000,
      "total_no_data_time_milli": 0,
      "total_light_sleep_time_milli": 12600000,
      "total_slow_wave_sleep_time_milli": 6000000,
      "total_rem_sleep_time_milli": 7800000,
      "sleep_cycle_count": 4,
      "disturbance_count": 2
    },
    "sleep_needed": {
      "baseline_milli": 27360000,
      "need_from_sleep_debt_milli": 1800000,
      "need_from_recent_strain_milli": 900000,
      "need_from_recent_nap_milli": -1200000
    },
    "respiratory_rate": 16.1,
    "sleep_performance_percentage": 98.0,
    "sleep_consistency_percentage": 90.0,
    "sleep_efficiency_percentage": 91.7
  }
}
```

**Notes:**
- `v1_id` is a legacy integer ID (deprecated). May be null.
- `score` is only present when `score_state` is `SCORED`
- Stage summary times are in milliseconds (int64)

---

## Recovery

### GET /v2/recovery
**Scope:** `read:recovery` | **Paginated** (same params as Cycle)

### GET /v2/cycle/{cycleId}/recovery
**Scope:** `read:recovery`

### Recovery Response

```json
{
  "cycle_id": 12345678,
  "sleep_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 12345,
  "created_at": "2024-01-16T07:00:00.000Z",
  "updated_at": "2024-01-16T07:00:00.000Z",
  "score_state": "SCORED",
  "score": {
    "user_calibrating": false,
    "recovery_score": 78.0,
    "resting_heart_rate": 52.0,
    "hrv_rmssd_milli": 65.4,
    "spo2_percentage": 97.5,
    "skin_temp_celsius": 33.2
  }
}
```

**Recovery zones:**
- Green (67-100%): Ready for high strain
- Yellow (34-66%): Moderate strain appropriate
- Red (0-33%): Rest/active recovery recommended

**Notes:**
- `recovery_score` and `resting_heart_rate` are floats, not integers
- `spo2_percentage` and `skin_temp_celsius` require WHOOP 4.0+
- `score` is only present when `score_state` is `SCORED`

---

## Workout

### GET /v2/activity/workout/{workoutId}
**Scope:** `read:workout` | **Param:** `workoutId` (UUID string)

### GET /v2/activity/workout
**Scope:** `read:workout` | **Paginated** (same params as Cycle)

### Workout Response

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "v1_id": null,
  "user_id": 12345,
  "created_at": "2024-01-15T17:00:00.000Z",
  "updated_at": "2024-01-15T18:15:00.000Z",
  "start": "2024-01-15T17:00:00.000Z",
  "end": "2024-01-15T18:05:00.000Z",
  "timezone_offset": "+01:00",
  "sport_id": 0,
  "sport_name": "Running",
  "score_state": "SCORED",
  "score": {
    "strain": 14.2,
    "average_heart_rate": 155,
    "max_heart_rate": 182,
    "kilojoule": 1850.5,
    "percent_recorded": 100.0,
    "distance_meter": 8500.0,
    "altitude_gain_meter": 45.2,
    "altitude_change_meter": 2.1,
    "zone_durations": {
      "zone_zero_milli": 60000,
      "zone_one_milli": 300000,
      "zone_two_milli": 900000,
      "zone_three_milli": 1500000,
      "zone_four_milli": 1080000,
      "zone_five_milli": 60000
    }
  }
}
```

**Notes:**
- `v1_id` is a legacy integer ID (deprecated). May be null.
- `score` can be **null** for non-strain activities (sauna, meditation, ice bath)
- `score` is only present when `score_state` is `SCORED`
- Zone durations are in milliseconds (int64)
- The field is `zone_durations` (plural)

---

## Activity Mapping

### GET /v1/activity-mapping/{activityV1Id}
Map legacy v1 integer ID to v2 UUID. **Param:** `activityV1Id` (integer)

```json
{ "v2_activity_id": "550e8400-e29b-41d4-a716-446655440000" }
```

---

## Data Models

### WHOOP Domain Concepts

**Strain (0-21):** Cardiovascular load based on Borg Scale. Non-linear — going from 16→17 requires more exertion than 4→5. Accumulates throughout the day from all activities.
- Light: 0-9 | Moderate: 10-13 | High: 14-17 | All Out: 18-21

**Recovery (0-100%):** Morning readiness assessment from RHR, HRV, respiratory rate, sleep quality, SpO2, skin temp.
- Green: 67-100% | Yellow: 34-66% | Red: 0-33%

**Sleep Performance:** Percentage of sleep need achieved. Sleep need = baseline + debt + strain adjustment - nap credit.

**HRV (RMSSD):** Root Mean Square of Successive RR interval Differences in milliseconds. Higher = better parasympathetic recovery.

### Timestamps
All timestamps are ISO 8601 format with milliseconds: `2024-01-15T17:00:00.000Z`

### ID Types
- Cycle: `int64`
- Sleep: `UUID string`
- Workout: `UUID string`
- Recovery: accessed via `cycle_id` (int64) or `sleep_id` (UUID)
- User: `int64`

## Score States

| State | Meaning |
|-------|---------|
| `SCORED` | Complete — `score` object populated |
| `PENDING_SCORE` | Processing — `score` absent, check back later |
| `UNSCORABLE` | Insufficient data — `score` absent |

## Sport Types

Common sport IDs (100+ supported):

| ID | Sport | ID | Sport |
|----|-------|----|-------|
| -1 | Activity | 0 | Running |
| 1 | Cycling | 16 | Baseball |
| 17 | Basketball | 18 | Rowing |
| 21 | Football | 24 | Golf |
| 25 | Ice Hockey | 27 | Rugby |
| 28 | Sailing | 29 | Skiing |
| 30 | Soccer | 31 | Softball |
| 32 | Squash | 33 | Swimming |
| 34 | Tennis | 35 | Track & Field |
| 36 | Volleyball | 38 | Wrestling |
| 39 | Boxing | 42 | Dance |
| 43 | Pilates | 44 | Yoga |
| 45 | Weightlifting | 47 | Cross Country Skiing |
| 48 | Functional Fitness | 51 | Gymnastics |
| 52 | Hiking/Rucking | 55 | Kayaking |
| 56 | Martial Arts | 57 | Mountain Biking |
| 59 | Powerlifting | 60 | Rock Climbing |
| 61 | Paddleboarding | 62 | Triathlon |
| 63 | Walking | 64 | Surfing |
| 65 | Elliptical | 66 | Stairmaster |
| 70 | Meditation | 71 | Other |
| 82 | Ultimate | 84 | Jumping Rope |
| 88 | Ice Bath | 89 | Commuting |
| 90 | Gaming | 91 | Snowboarding |
| 96 | HIIT | 97 | Spin |
| 98 | Jiu Jitsu | 99 | Manual Labor |
| 100 | Cricket | 101 | Pickleball |
| 123 | Strength Trainer | 126 | Assault Bike |
| 127 | Kickboxing | 128 | Stretching |
| 230 | Table Tennis | 231 | Badminton |
| 233 | Sauna | 234 | Disc Golf |
| 235 | Yard Work | 236 | Air Compression |
| 239 | Ice Skating | 240 | Handball |
| 249 | Padel | 259 | Hot Yoga |
| 264 | Kite Boarding | 266 | Dog Walking |
| 269 | Cooking | 270 | Cleaning |
| 272 | Public Speaking | | |

The `sport_id` is an integer and `sport_name` is returned alongside it. Use `sport_name` for display; use `sport_id` for filtering/grouping.

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 204 | Success (no content) |
| 400 | Client error constructing request |
| 401 | Invalid or expired authorization |
| 404 | Resource not found |
| 429 | Rate limited |
| 500 | Server error |
