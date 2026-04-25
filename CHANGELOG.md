# Changelog

Initial version: `2026.04.25_1900`

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
