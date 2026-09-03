# Plexio: Plex Interaction for Stremio

⚠️ Plexio is an independent project and is not in any way affiliated with Plex or Stremio. ⚠️

Plexio is an addon that bridges the gap between Plex and Stremio, enabling seamless 
integration of your Plex media within the Stremio interface. With Plexio, you can discover 
and stream your Plex content directly in Stremio.

### Features
* offers both direct and transcoded streams;
* stream locally or from remote devices;
* allows searching through your Plex library;
* works with Cinemeta and other IMDB-based addons;
* handles media without IMDB matching;
* uses OAuth for safe login without sharing passwords;
* protects each addon configuration with its own optional password (or none);
* server-side admin page (gated by `MANAGE_KEY`) with global settings and
  recorded installations;
* fully open-source with self-hosting support.

## Passwords, two levels

Like the reference stremio-jellyfin fork, Plexio has two independent password
levels:

* **Per configuration** — every addon install link (`/…/…/configure`) can be
  locked with its own password, or left open (default). Unlocking is
  stateless: the password is validated for the current page load only, no
  cookie is kept, so reloading the Configure page asks for it again. The
  server admin can reset a lost lock from the same card. Managing the lock
  happens on the Configure page, in the *Configuration password* card.
* **Server admin** (`MANAGE_KEY` or the /admin page) — gates only `/admin`.
  It never blocks the Configure page.

## Admin page

Point your browser to `<addon-origin>/admin` for the server admin page. What
you can do there (it requires the admin password when one is set):

* **Server settings** — server-wide toggles, persisted in the database and
  applied to every addon configuration:
  * *Stream proxy* (`proxy_enabled`): master switch for the media relay. When
    off, every relay request is refused with `403` regardless of what an addon
    config requests.
  * *Admin-only proxy toggle* (`proxy_admin_only`): when on, the proxy toggle
    in the Configure page is only shown to admin sessions.
* **Manage password** — set the initial admin password when none is configured
  yet, or change the existing one. If the operator set `MANAGE_KEY` in the
  environment, the API password is managed there and cannot be changed from
  the page.
* **Installations** — a privacy-minimized list of addon configurations that
  were saved by an admin from the Configure page (name, server count, date),
  with the ability to remove records. No access tokens are ever returned by
  the list endpoint.


## Self-Hosting
If you'd prefer to self-host Plexio, you can do so easily using Docker. Follow these steps:

1. Use the following command to start a Plexio instance:
   ```bash
   docker run -d -p 7777:80 ghcr.io/vanchaxy/plexio
   ```
2. Plexio addon will be available at http://localhost:7777/.

### Optional Configuration with Environment Variables
* *CORS_ORIGIN_REGEX*: A regex pattern to define allowed CORS origins 
(default: `https?:\/\/localhost:\d+|.*plexio.stream|.*strem.io|.*stremio.com`).
* *PLEX_REQUESTS_TIMEOUT*: Timeout for Plex server requests in seconds (default: `20`).
* *CACHE_TYPE*: Defines the cache type to use `memory`/`redis` (default: `memory`).
* *REDIS_URL*: URL for a Redis instance if you use `redis` cache (default: `redis://redis:6399/0`).
* *PLEX_MATCHING_TOKEN*: Auth token for Plex media matching (default: `None`).
* *SENTRY_DSN*: DSN for error tracking with Sentry (default: `None`).
* *DB_PATH*: SQLite file for server-owned settings — the manage password hash,
  the proxy-token encryption secret, admin toggles and recorded installations
  persist here across restarts (`default: :memory:`, i.e. in-process only). In
  Docker, mount a volume at the default `/app/data` so the database survives
  container recreation.
* *MANAGE_KEY*: Server admin password, protecting only the `/admin` page.
  When set, a password screen (admin session cookie) is required before it
  loads; it also unlocks the stream-proxy toggle. Per-configuration passwords
  are independent and live in the database. Leave empty to keep `/admin`
  open.
* *PROXY_ENABLED*: Server-wide master switch for the media relay. When `false`,
  the relay refuses every request regardless of config (default: `true`).
* *PROXY_ADMIN_ONLY*: When `true`, the stream-proxy toggle is only offered to
  admin sessions (default: `true`).
* *MANAGE_COOKIE_SECURE*: Mark the admin cookie `Secure` (HTTPS only)
  (default: `true`). Set to `false` only for plain-HTTP testing.

### Using addon with shared Plex server
If you are using Plexio with a Plex server that you do not own (you will see a "shared" badge 
next to the server name), you must provide the `PLEX_MATCHING_TOKEN` environment variable. 
This token is an access token from a Plex server you own, which will be used to
query the Plex API and resolve the Plex GUID using IMDB IDs.

To find your Plex authentication token, open any media on a Plex server you own.
Look for the XML data for the media and find the `X-Plex-Token` in the URL. 
Copy the token from the URL.

You can learn more about finding your authentication token in the official Plex article 
["Finding an authentication token"](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

## Per-user endpoint (`/u/<uid>`)

After Plex OAuth login the frontend derives a stable `uid` from the Plex
account (numeric `id` → `uuid` → `username`, via `derivePlexUid`) and
redirects `/` → `/u/<uid>`. Your personal configure page lives at
`/u/<uid>` (and `/u/<uid>/configure`). Bookmark it to edit the same setup
later — the bookmark is scoped to your Plex user, not shared globally.

Install links are built under that prefix:

* **Stored mode** (single config per Plex user, bookmarked page):
  `/u/<uid>/manifest.json` — served directly from the DB without exposing the
  base64 token. Stremio install uses the `stremio://` variant of the same URL.
* **Token mode** (portable, stateless):
  `/u/<uid>/<installation_id>/<base64_cfg>/manifest.json`
  and the same shape for catalog/meta/stream.
  Example: `https://plexio.example.com/u/123/abc123/eyJzZXJ2.../manifest.json`

`uid`, `installation_id`, and `base64_cfg` stay URL-safe (`urlsafe_b64encode`
without padding). `uid` is treated as an opaque string throughout the
frontend (`ConfigRoute.uid`) and as a path param on the backend.

Backward compatibility is fully preserved:

* `/{id}/{token}/manifest.json` (and catalog/meta/stream) keep working.
* `/u/<id>/manifest.json` (legacy bookmark without `uid` prefix) keeps
  working — when the DB entry is valid JSON it is served directly (200
  `StremioManifest`), otherwise it 302-redirects to the legacy install URL.
* `/u/<id>` and `/u/<id>/configure` keep 302-redirecting to
  `/{id}/{token}/configure` for old bookmarks.

SPA fallback: `/u/<uid>` is a client-side route. In local dev, `nginx-local.conf`
proxies `location /` to Vite (`frontend:5173`), which has built-in history
fallback. In production, `unit-nginx-config.json` shares
`/app/frontend$uri` with `fallback: /app/frontend/index.html`, so any
non-`/api` and non-`*json` `/u/<uid>` request serves `index.html` for
`react-router` (`BrowserRouter` with `path="/u/:uid"` and `path="/u/:uid/*"`).
No additional nginx `try_files` is needed beyond that fallback.

## Local Development
1. Fork the Repository.
2. Clone the Repository:
   ```bash
   git clone https://github.com/yourusername/plexio.git
   ```
3. Create a `.env` file and configure the required environment variables.
4. Run doker-compose:
   ```bash
   docker-compose up --build
   ```

## Contacts

For bug reports, feature requests, or general questions, join our
[Discord support forum](https://discord.gg/8RWUkebmDs).

Alternatively, you can open an issue directly in this repository.

