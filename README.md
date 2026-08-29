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
  locked with its own password, or left open (default). Whoever sets a
  password must type it to open the Configure page again; the server admin can
  reset a lost lock from the same card. Managing the lock happens on the
  Configure page, in the *Configuration password* card.
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

