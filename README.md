# [IPv64.net](https://ipv64.net/account?p=fK4RZo) | Free DynDNS2 & Healthcheck Service | Integration for Home-Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://img.shields.io/badge/My-HACS:%20REPOSITORY-000000.svg?&style=for-the-badge&logo=home-assistant&logoColor=white&color=049cdb)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Ludy87&repository=ipv64&category=integration)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge&logo=home-assistant&logoColor=white)](https://github.com/hacs/integration)
![Validate with hassfest and HACS](https://img.shields.io/github/actions/workflow/status/Ludy87/ipv64/hassfest.yaml?label=Validate%20with%20hassfest%20and%20hacs&style=for-the-badge&logo=home-assistant&logoColor=white)\
[![GitHub license](https://img.shields.io/github/license/Ludy87/ipv64?label=📜%20License&style=for-the-badge&logo=informational&logoColor=white)](LICENSE)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/Ludy87/ipv64?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/Ludy87/ipv64/releases)
![GitHub Release Date](https://img.shields.io/github/release-date/Ludy87/ipv64?style=for-the-badge&logo=GitHub&logoColor=white)
[![GitHub stars](https://img.shields.io/github/stars/Ludy87/ipv64?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/Ludy87/ipv64/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Ludy87/ipv64?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/Ludy87/ipv64/issues)
![Github All Releases](https://img.shields.io/github/downloads/Ludy87/ipv64/total.svg?style=for-the-badge&logo=GitHub&logoColor=white)\
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge&logoColor=white)\
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Ludy87/ipv64/main.svg?style=for-the-badge&logoColor=white)](https://results.pre-commit.ci/latest/github/Ludy87/ipv64/main)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/9869/badge)](https://www.bestpractices.dev/projects/9869)\
[![✨ Wishlist from Amazon ✨](https://img.shields.io/static/v1.svg?label=✨%20Wishlist%20from%20Amazon%20✨&message=📖&color=green&logo=amazon&style=for-the-badge&logoColor=white)](https://smile.amazon.de/registry/wishlist/2MX8QK8VE9MV1)
[![Buy me a coffee](https://img.shields.io/static/v1.svg?label=Buy%20me%20a%20coffee&message=donate&style=for-the-badge&color=black&logo=buy%20me%20a%20coffee&logoColor=white&labelColor=orange)](https://www.buymeacoffee.com/ludy87)

---

[![IPv64.net](https://github.com/Ludy87/ipv64/blob/main/images/ipv64_logo.png?raw=true)](https://ipv64.net/account?p=fK4RZo)

## Overview

[IPv64.net](https://ipv64.net/account?p=fK4RZo) provides a free Dynamic DNS (DynDNS) and Healthcheck service, allowing you to manage domains and keep devices accessible despite changing IP addresses. The name "IPv64" is a playful combination of IPv6 and IPv4, not a new protocol. This integration enables Home Assistant users to manage their IPv64.net domains, monitor IP updates, and leverage features like DDoS protection, GEO load balancing, and Let's Encrypt DNS challenges.

With this integration, you can:

- [Register and manage free subdomains (e.g., `yourname.ipv64.net` or `prefix.yourname.home64.de`).](https://ipv64.net/account?p=fK4RZo)
- Update IP addresses automatically or manually.
- Add or delete domains via the [IPv64.net](https://ipv64.net/account?p=fK4RZo) API.
- Monitor remaining daily update tokens (default: 64 per day).
- Enable Economy Mode to save tokens by updating only when the IP changes.

---

## Prerequisites

To use this integration, you need:

- An [IPv64.net](https://ipv64.net/account?p=fK4RZo) account.
- An **API Key** and **Account Update Token** from your [IPv64.net](https://ipv64.net/account?p=fK4RZo) account.
- A valid domain registered with IPv64.net (e.g., `yourname.ipv64.net` or `prefix.yourname.home64.de`).
- Home Assistant installed and running.

> **Note**: Register for free at [IPv64.net](https://ipv64.net/account?p=fK4RZo) to obtain your API Key and Account Update Token.

---

## Installation

### Option 1: Install via HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. Go to **HACS > Integrations > Explore & Download Repositories**.
3. Search for **IPv64 Integration** and click **Download**.
4. Restart Home Assistant when prompted.

### Option 2: Manual Installation

1. Download the [latest release](https://github.com/Ludy87/ipv64/releases) of the IPv64 integration.
2. Copy the `ipv64` folder and its contents to your Home Assistant `custom_components` directory (typically located at `/config/custom_components/`).
   - For **Hass.io** users, use SAMBA to copy the folder.
   - For **Home Assistant Supervised**, the folder may be at `/usr/share/hassio/homeassistant`.
3. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, navigate to **Settings > Devices & Services > Add Integration** (+ button).
2. Search for **IPv64** and select it.
3. Enter your **API Key**, **Account Update Token**, and **Domain** (e.g., [`yourname.ipv64.net`](https://ipv64.net/account?p=fK4RZo)).
4. Configure optional settings:
   - **Economy Mode**: Enable to update the IP only when it changes (checked via `https://checkip.amazonaws.com/`), saving API tokens.
   - **Update Interval**: Set the polling interval (0–120 minutes; default: 23 minutes). Set to 0 to disable automatic updates.
5. Submit the configuration. The integration will appear as a card on the **Devices & Services** page.

---

## Services

This integration provides the following services:

- **Refresh IP Address** (`ipv64.refresh`):
  - Manually updates the IP address for the configured domain.
  - **Parameter**: `economy` (boolean) – Enable Economy Mode to update only if the IP has changed.
  - **Note**: Each update consumes one of the 64 daily tokens.

- **Add Domain** (`ipv64.add_domain`):
  - Creates a new domain via the IPv64.net API (e.g., `test1234.any64.de`).
  - **Parameter**: `domain` (text) – The domain to create, which must be one of the allowed domains (see below).

- **Delete Domain** (`ipv64.delete_domain`):
  - Deletes an existing domain via the IPv64.net API.
  - **Parameter**: `domain` (text) – The domain to delete.

**Allowed Domains**:

- `ipv64.net`, `ipv64.de`, `any64.de`, `eth64.de`, `home64.de`, `iot64.de`, `lan64.de`, `nas64.de`, `srv64.de`, `tcp64.de`, `udp64.de`, `vpn64.de`, `wan64.de`, `api64.de`, `dyndns64.de`, `dynipv6.de`, `dns64.de`, `root64.de`, `route64.de`

---

## Sensors

The integration creates the following sensors:

- **IPv64 [Domain] Status**: Displays the status of the DynDNS update (e.g., `success` or `fail`).
- **IPv64 [Domain] IP**: Shows the current IP address associated with the domain.
- **IPv64 [Domain] DynDNS Counter Today**: Tracks the number of updates used today.
- **IPv64 [Domain] Remaining Updates**: Shows the remaining daily update tokens (out of 64).

---

## Debugging

To enable debug logging for troubleshooting, add the following to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.ipv64: debug
```

---

## Support

- **Documentation**: [GitHub Repository](https://github.com/Ludy87/ipv64)
- **Issue Tracker**: [GitHub Issues](https://github.com/Ludy87/ipv64/issues)
- **Community**: Join the [Discord server](https://discord.gg/rpicloud)
- **Tutorials**: Check out the [YouTube channel](https://youtube.com/c/RaspberryPiCloud)
- **Blog**: Visit [schroederdennis.de](https://schroederdennis.de/d)
- **Twitter**: Follow [@dennis_schroed](https://twitter.com/dennis_schroed)

---

## Contributing

Contributions are welcome! Please submit issues or pull requests to the [GitHub repository](https://github.com/Ludy87/ipv64).

If you find this integration helpful, consider supporting the project:

- [Buy me a coffee](https://www.buymeacoffee.com/ludy87)
- [Amazon Wishlist](https://smile.amazon.de/registry/wishlist/2MX8QK8VE9MV1)
- [Ipv64.net](https://ipv64.net/account?p=fK4RZo)
