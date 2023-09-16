# IPv64.net | Free DynDNS2 & Healthcheck Service | Integration for Home-Assistant

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
[![✨ Wishlist from Amazon ✨](https://img.shields.io/static/v1.svg?label=✨%20Wishlist%20from%20Amazon%20✨&message=📖&color=green&logo=amazon&style=for-the-badge&logoColor=white)](https://smile.amazon.de/registry/wishlist/2MX8QK8VE9MV1)
[![Buy me a coffee](https://img.shields.io/static/v1.svg?label=Buy%20me%20a%20coffee&message=donate&style=for-the-badge&color=black&logo=buy%20me%20a%20coffee&logoColor=white&labelColor=orange)](https://www.buymeacoffee.com/ludy87)

---

![IPv64](https://github.com/Ludy87/ipv64/blob/main/images/ipv64_logo.png?raw=true)

## What is IPv64.net?

IPv64 is of course not a new Internet Protocol (64), but simply a deduplicated short form of IPv6 and IPv4. On the IPv64 site you will find a Dynamic DNS service (DynDNS) and many other useful tools for your daily internet experience.

With the dynamic DNS service of IPv64 you can register and use free subdomains. The update of the domain is done automatically by your own router or alternative hardware / software. Besides updating IP addresses, simple Let's Encrypt DNS challenges are also possible.

Own domains can be added and benefit from all IPv64.net features like DynDNS services, GEO load balancing, DDoS protection, DynDNS2 and SSL encryption.

[![Register now for free](https://img.shields.io/static/v1.svg?label=&message=Register%20now%20for%20free&style=for-the-badge&color=blue)](https://ipv64.net/account.php)\
[![Discord](https://img.shields.io/static/v1.svg?label=Discord&message=rpicloud&style=for-the-badge&color=black&logo=discord&logoColor=white&labelColor=blue)](https://discord.gg/rpicloud)
[![Youtube](https://img.shields.io/static/v1.svg?label=Youtube&message=rpicloud&style=for-the-badge&color=black&logo=youtube&logoColor=white&labelColor=red)](https://youtube.com/c/RaspberryPiCloud)
[![Twitter](https://img.shields.io/static/v1.svg?label=Twitter&message=rpicloud&style=for-the-badge&color=black&logo=twitter&logoColor=white&labelColor=blue)](https://twitter.com/dennis_schroed)
[![Blog Schroederdennis.de](https://img.shields.io/static/v1.svg?label=Blog&message=rpicloud&style=for-the-badge&color=black&logo=twitter&logoColor=white&labelColor=grey)](https://schroederdennis.de/d)

---

> ## _You need an Account Update Token and an API key to access the IPv64.net API._

## Installation

### MANUAL INSTALLATION

Copy the ipv64 [last Releae](https://github.com/Ludy87/ipv64/releases) folder and all of its contents into your Home Assistant's custom_components folder. This folder is usually inside your /config folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the custom_components folder might be located at /usr/share/hassio/homeassistant. You may need to create the custom_components folder and then copy the localtuya folder and all of its contents into it Alternatively, you can install localtuya through HACS by adding this repository.

### INSTALLATION mit HACS

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Search for and install the "**ipv64 Integration**" integration. [![GitHub release (latest by date)](https://img.shields.io/github/v/release/Ludy87/ipv64?style=for-the-badge&logo=GitHub)](https://github.com/Ludy87/ipv64/releases)
3. [Configuration for the `ipv64` integration is now performed via a config flow as opposed to yaml configuration file.](https://github.com/Ludy87/ipv64#basis-configuration)
4. Restart Home Assistant.

---

## Basis Configuration

1. Go to HACS -> Integrations -> Click "+"
2. Search for "ipv64" repository and add to HACS
3. Restart Home Assistant when it says to.
4. In Home Assistant, go to Configuration -> Integrations -> Click "+ Add Integration"
5. Search for "ipv64" and follow the instructions to setup.

ipv64 should now appear as a card under the HA Integrations page with "Configure" selection available at the bottom of the card.

---

## API Key Sparing

There is a switch to prevent the API key (default: 64) from being used up. The last IP address and the current IP address are compared (<https://checkip.amazonaws.com/>), if it is negative, the IP update function of IPv64.net is called.

---

## Debug

```yaml
logger:
  logs:
    custom_components.ipv64: debug
```

---
