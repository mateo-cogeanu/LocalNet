# Changelog

Initial version: `2026.04.25_1900`

## 2026.04.26_1928

- Fixed the offline wiki archive-root case so links to `/offlinewiki/content/<archive-slug>` no longer get incorrectly rewritten into `/offlinewiki/content/<archive-slug>/<archive-slug>`.
- Restored proper Kiwix handling for archive landing pages, including the built-in redirect to that archive's `/index` page.

## 2026.04.26_1916

- Added an offline wiki compatibility shim for archive-less Kiwix article links such as `/offlinewiki/content/<title>`.
- LocalNet now inserts the active ZIM archive slug automatically for those links, fixing false not-found pages on article clicks like `List_of_states_and_territories_of_the_United_States`.

## 2026.04.26_1910

- Fixed the offline wiki proxy to forward Kiwix requests using the raw incoming URL instead of rebuilding paths from Flask-decoded route pieces.
- Improved article navigation reliability for Wikipedia pages whose links use relative titles or encoded characters, so clicking into articles no longer falls into false not-found pages.

## 2026.04.26_1145

- Made the offline library detect `kiwix-serve` live instead of caching the result at app startup, so installing the server bundle no longer forces a fragile path guess.
- Added support for a local `tools/kiwix-tools` server bundle and auto-normalized mislabeled `.zim.zip` archives into real `.zim` files when they are actually ZIM data.

## 2026.04.26_1138

- Added macOS app-bundle detection for `kiwix-serve`, so LocalNet can use the binary shipped inside the Kiwix app even when Homebrew does not provide a `kiwix-tools` formula.
- Updated the Offline Wiki Reader install hint to use the working Homebrew cask command for Kiwix on macOS.

## 2026.04.26_1132

- Added an embedded Offline Wiki Reader flow so downloaded Wikipedia archives can be opened inside LocalNet instead of only being treated as files.
- Wired LocalNet to `kiwix-serve` with a prefixed reader mount and a built-in proxy route, so the archive can be browsed through the app when the host has Kiwix installed.

## 2026.04.26_1130

- Fixed the Offline Library so completed Wikipedia downloads show up even when the saved file on disk uses a slightly different suffix than the preset expected.
- Kept library links tied to the actual downloaded file path instead of assuming every Kiwix file lands with the exact preset filename.

## 2026.04.26_1128

- Removed the old seed-pack naming from the admin setup area so the offline library tools read more naturally inside LocalNet.
- Added a real Offline Library page for downloaded Wikipedia archives, with direct file access from inside the app.
- Added live ZIM download progress polling and progress bars in Settings so background downloads no longer look stuck or vague.

## 2026.04.26_1124

- Stopped tracking runtime JSON data and uploaded media in git so user comments, uploads, and other live LocalNet content stay local to the host machine.
- Kept the host-managed `data/admins.txt` file outside that ignore rule so admin access can still be configured on the machine.

## 2026.04.26_1118

- Added a Notifications page with unread counts in the nav, plus notification events for DMs, likes, comments, and selected wiki/forum activity.
- Added a new Music app with track uploads, playback, likes, comments, editing, and deletion.
- Added an admin-only Setup tab in Settings that exposes wiki seed packs and official Kiwix Wikipedia ZIM download presets with background job tracking.

## 2026.04.25_2203

- Added deeper browser-side microphone diagnostics for DM calling, including raw WebRTC error details and visible audio-input counts.
- Improved the Firefox call failure toasts so microphone issues can be distinguished from browser device-detection problems.

## 2026.04.25_2201

- Fixed the DM voice-call error handling so LocalNet no longer blames microphone permission for every call failure after access has already been allowed.
- Added clearer call setup messages for blocked permission, missing mic hardware, busy devices, and generic WebRTC setup failures.

## 2026.04.25_2159

- Improved DM voice-call playback for Firefox by explicitly starting the remote audio element when the call connects and when tracks arrive.
- Added a clearer fallback toast for browsers that still require an extra user gesture before remote call audio can play.

## 2026.04.25_2150

- Added proxy-aware HTTPS support in the Flask app so LocalNet behaves correctly behind TLS and can use secure cookies for phone access.
- Added a Caddy-based local HTTPS setup with [Caddyfile](/Users/mateocogeanu/Downloads/LocalNet/Caddyfile) and [HTTPS.md](/Users/mateocogeanu/Downloads/LocalNet/HTTPS.md) for phone-ready voice calls.

## 2026.04.25_2140

- Added DM voice calling with WebRTC audio, including call invite, accept or decline, ringing, mute, hang up, and disconnect cleanup.
- Upgraded the chat header with a real call panel and incoming-call banner so voice calls feel built into LocalNet instead of bolted on.

## 2026.04.25_2132

- Rebuilt the homepage hero blobs as separate animated layers so they visibly drift instead of blending into one mushy glow.
- Spread the hero lighting out more cleanly so the `⟨LocalNet⟩` landing area feels more alive and less clumped together.

## 2026.04.25_2127

- Reworked the top navigation to feel more alive with subtle drifting light and motion instead of a static strip.
- Removed the blue-ish hover and active feel from the menu so navigation highlights stay neutral and glassy.
- Deepened the app-wide gradient layering and smoothing so backgrounds feel cleaner and less like compressed video.

## 2026.04.25_2120

- Smoothed the app-wide gradient system so backgrounds and surfaces feel less layered and more continuous.
- Added subtle animated homepage blob motion behind the `⟨LocalNet⟩` hero for a more alive landing experience.
- Reworked mobile navigation into a collapsible menu instead of relying on cramped wrapped links.
- Added a host-managed `data/admins.txt` file and gold admin badges across the main UI and chat.

## 2026.04.25_2116

- Removed the boxed-looking hero slab on the homepage so the ambient gradient flows through the `⟨LocalNet⟩` area more naturally.

## 2026.04.25_2048

- Made login sessions persistent across app restarts by storing a stable LocalNet secret key instead of generating a new one each launch.
- Changed 2FA into a separate second step so password entry succeeds first and the code is requested on the next screen without making you type the password again.

## 2026.04.25_1953

- Made pinned favorites more compact so they show as small icon-and-name pills under `⟨LocalNet⟩`.
- Added profile customization in Settings with bio, profile picture, and banner uploads plus a live-style profile preview.
- Added password change and account deletion flows in Settings.
- Fixed the navigation settings icon and upgraded the user chip to show the current profile picture when available.
- Added subforums and a more polished forum browse experience with category cards and profile-aware thread/comment avatars.
- Added direct messages to Chat alongside the shared lobby, including conversation history and online-user DM starts.

## 2026.04.25_1943

- Restyled Tube and Games into a more YouTube-like browse layout with wider thumbnail cards, avatar-style author badges, and tighter metadata spacing.
- Kept the card sizing responsive so the browse pages feel familiar without stretching single items awkwardly.

## 2026.04.25_1937

- Tightened Tube and Games into more compact horizontal media rows so uploads stop feeling oversized.
- Kept homepage pins directly under `⟨LocalNet⟩` with the SVG pen control for editing pinned sites.
- Continued release tracking with a new timestamped changelog section instead of folding everything into the initial version.

## 2026.04.25_1900

- Rebuilt the missing Python backend with Flask and Flask-SocketIO in `app.py`.
- Restored data persistence using JSON files in `data/` and upload storage in `uploads/`.
- Added backend support for login, auto-registration, logout, optional 2FA setup and verification, Tube uploads and comments, Games uploads, Paste, Wiki, Forums, Settings, and live Chat.
- Added `requirements.txt` for the Python server dependencies.
- Added the missing client assets in `static/css/style.css` and `static/js/main.js`.
- Added `templates/home.html` and `templates/forums.html` to support the homepage and forums routes.
- Updated the login flow so the 2FA field only appears when a user account actually requires it.
- Updated Tube and Games list pages to use normal-sized open buttons instead of whole-card oversized click targets.
- Reworked the homepage into a centered `⟨LocalNet⟩` hub with pin-able favorite site shortcuts.
- Polished the overall visual design to feel less boxy, including softer surfaces, improved branding, and consistent `⟨LocalNet⟩` naming across the main UI.
- Added a basic `.gitignore` and prepared the project for publishing to GitHub.
