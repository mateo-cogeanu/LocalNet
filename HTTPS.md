# HTTPS Setup

LocalNet phone voice calls need `https://` so the browser will allow microphone access.

## 1. Install Caddy

On macOS with Homebrew:

```bash
brew install caddy
```

## 2. Find your LAN IP

Example:

```bash
ipconfig getifaddr en0
```

If `en0` is not your active network interface, use the one that is connected.

## 3. Start LocalNet behind HTTPS

Replace `192.168.1.50` with your real LAN IP:

```bash
LOCALNET_HTTPS=1 LOCALNET_PORT=2453 python3 app.py
```

In another terminal:

```bash
LOCALNET_HOST=192.168.1.50 LOCALNET_PORT=2453 caddy run --config Caddyfile
```

Then open this on your phone:

```text
https://192.168.1.50
```

## 4. Trust the Caddy local certificate

The phone must trust Caddy's local CA certificate or the browser will still warn/block.

On the machine running Caddy, export the root certificate:

```bash
caddy trust
```

The root certificate is usually here on macOS:

```text
~/Library/Application Support/Caddy/pki/authorities/local/root.crt
```

Install that certificate on your phone and mark it as trusted.

## Notes

- Keep Flask running on port `2453`.
- Let Caddy handle `https://`.
- LocalNet now respects proxy HTTPS headers and secure cookies when `LOCALNET_HTTPS=1`.
- If you want a cleaner hostname later, we can switch from a raw IP to a local domain.
