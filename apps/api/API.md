# Futnet Nepal Mobile API (v1)

Base URL: `/api/v1/`

## Authentication

Use JWT in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `auth/register/` | No | Create account (email verification required) |
| POST | `auth/login/` | No | `{ "login": "user or email", "password": "..." }` → tokens + user |
| POST | `auth/token/refresh/` | No | `{ "refresh": "..." }` → new access token |
| POST | `auth/verify-email/` | No | `{ "token": "..." }` |
| POST | `auth/resend-verification/` | No | `{ "email": "..." }` |
| GET/PATCH | `auth/me/` | Yes | Current user + profile + stats |
| GET | `profile/stats/` | Yes | Activity stats |

## Reference data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `locations/` | All locations |
| GET | `times/` | Time slots |
| GET | `venues/` | Venues (`?search=` via router if added) |
| GET | `venues/<slug>/` | Venue detail |

## Matches (posts)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `posts/` | Feed (`?time=<slug>`, `?author=me`) |
| POST | `posts/` | Create match |
| GET/PATCH/DELETE | `posts/<id>/` | Detail / update / delete |
| POST | `posts/<id>/interest/` | Toggle interested |
| POST | `posts/<id>/react/` | Toggle like |
| GET | `posts/<id>/comments/` | Comment tree |
| POST | `posts/<id>/comments/add/` | `{ "body": "...", "parent_id": null }` |
| POST | `posts/<id>/confirm-match/` | Host confirm |
| POST | `posts/<id>/cancel-confirmation/` | Host reopen |

## Venue bookings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `bookings/` | User's bookings |
| POST | `bookings/` | `{ "venue_id", "booking_date", "preferred_time", "notes" }` |

## Phone verification (Aakash SMS)

| Method | Path | Description |
|--------|------|-------------|
| POST | `auth/phone/send-otp/` | Body: `email`, `phone` — send 6-digit OTP |
| POST | `auth/phone/verify/` | Body: `email`, `phone`, `code` — confirm OTP |

Set `AAKASH_SMS_AUTH_TOKEN` in `.env`. Signup requires `phone` on register; login blocked until email and phone are verified.

**Flow:** email first, then phone. Web signup uses **email link**; mobile (`POST /auth/register/`) uses **6-digit email code**. Resend: `delivery` = `link` (web) or `code` (mobile).

| GET | `auth/verification-status/?email=` | `email_verified`, `phone_verified` |

## Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `notifications/` | Paginated list + `unread_count` |
| GET | `notifications/poll/?since_id=0` | New items since ID |
| POST | `notifications/<id>/read/` | Mark one read |
| POST | `notifications/read-all/` | Mark all read |

## Messaging

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `conversations/` | Inbox threads |
| GET | `conversations/<id>/` | Messages (`?after_id=`) |
| POST | `conversations/<id>/send/` | `{ "body": "..." }` |
| POST | `conversations/open/` | `{ "post_id", "username"? }` |
| POST | `conversations/<id>/confirm-attendance/` | Guest confirms |
| POST | `conversations/<id>/decline-attendance/` | Guest declines |
| POST | `conversations/<id>/confirm-match/` | Host confirm (in chat) |
| POST | `conversations/<id>/cancel-confirmation/` | Host reopen |

## Blogs (read-only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `blogs/` | List (`?category=`) |
| GET | `blogs/<slug>/` | Detail |
| GET | `blog-categories/` | Categories |

## Other

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `search/?q=term` | Yes | Posts, venues, users |
| POST | `contact/` | No | Public contact form |

## WebSockets (existing)

- `ws/notifications/` — live notifications (session auth today; add JWT middleware for mobile)
- `ws/dm/<conversation_id>/` — live DM

Poll HTTP endpoints work without WebSockets.
