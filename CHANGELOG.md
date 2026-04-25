# Changelog

Initial version: `2026.04.25_1900`

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
