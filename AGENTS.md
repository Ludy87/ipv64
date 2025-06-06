# Contributor Guide for IPv64 Integration

This guide provides instructions for contributing to the `ipv64` custom integration for Home Assistant. It outlines the development environment, testing procedures, and pull request (PR) guidelines to ensure consistent and high-quality contributions.

## Overview

The `ipv64` integration allows Home Assistant to interact with the IPv64.net API for managing dynamic DNS and related services. The codebase is located in the `custom_components/ipv64/` directory and consists of the following key files and folders:

- **`__init__.py`**: Initializes the integration and sets up services.
- **`config_flow.py`**: Handles the configuration flow for setting up the integration via the Home Assistant UI.
- **`coordinator.py`**: Manages data updates and API interactions with IPv64.net.
- **`sensor.py`**: Defines sensor entities for monitoring domain status, IP addresses, and other metrics.
- **`const.py`**: Contains constants used throughout the integration.
- **`manifest.json`**: Defines metadata and dependencies for the integration.
- **`my_submodule/`**: (Optional) A subdirectory for reusable helper functions or modules (not yet implemented but can be added for modularity).

### Key Areas for Contributions

- **Bug Fixes**: Address issues reported in the [issue tracker](https://github.com/Ludy87/ipv64/issues).
- **Feature Additions**: Add new sensors, services, or API endpoints.
- **Code Refactoring**: Improve code readability, performance, or compliance with Home Assistant standards.
- **Documentation**: Update `README.md`, `AGENTS.md`, or inline code comments.

## Dev Environment Tips

- **Setup**: Ensure you have a working Home Assistant instance (e.g., via Docker or a local installation). Copy the `ipv64` integration to the `custom_components/ipv64/` directory of your Home Assistant configuration.
- **Python Version**: Use Python 3.8 or higher, as required by Home Assistant.
- **Dependencies**: The integration requires `aiohttp>=3.11`, as specified in `manifest.json`. Install dependencies manually if testing outside Home Assistant:
  ```bash
  pip install aiohttp>=3.11
  ```
- **File Navigation**: Work primarily in `custom_components/ipv64/`. Use `grep` or an IDE to locate specific functions or constants across files.
- **Code Style**: Follow PEP 8 guidelines for Python code. Use type hints where possible, as seen in `sensor.py` and `coordinator.py`.
- **Logging**: Use the `_LOGGER` instance (from `logging.getLogger(__name__)`) for debug, warning, and error logs, as shown in existing files.

## Testing Instructions

- **Test Environment**: Run tests in a Home Assistant development environment. You can use the Home Assistant Dev Container or a local setup.
- **Linting**:
  - Run `pylint` to check for code style and potential errors:
    ```bash
    pylint custom_components/ipv64/*.py
    ```
  - Fix any reported issues to ensure compliance with PEP 8 and Home Assistant coding standards.
- **Unit Tests**:
  - The integration currently lacks unit tests. If you add tests, place them in a `tests/` directory (e.g., `tests/test_coordinator.py`) and use `pytest` with Home Assistant's testing framework:
    ```bash
    pytest tests/
    ```
  - Example test setup: Use `pytest-homeassistant-custom-component` for mocking Home Assistant components.
  - Ensure all tests pass before submitting a PR.
- **Manual Testing**:
  - Install the integration in a Home Assistant instance.
  - Add the integration via the UI (Settings > Devices & Services > Add Integration > IPv64).
  - Verify that sensors (e.g., `IPv64DynDNSStatusSensor`, `IPv64DomainSensor`) appear and update correctly.
  - Check logs for errors:
    ```bash
    tail -f /path/to/home-assistant.log
    ```
- **Validation**: After making changes, restart Home Assistant to reload the integration:
  ```bash
  hass --script restart
  ```
  Ensure no errors appear in the logs and that the integration functions as expected.

## PR Instructions

- **Title Format**: Use the format `[ipv64] <Descriptive Title>`. Example:
  ```
  [ipv64] Fix invalid via_device in IPv64BaseEntity
  ```
- **Description**: Include a clear description of the changes, the issue they address (if applicable), and any testing steps performed. Reference the issue number if it exists (e.g., `Fixes #123`).
- **Commits**: Write clear, concise commit messages. Example:
  ```
  Remove via_device from DeviceInfo in sensor.py to fix Home Assistant 2025.12.0 compatibility
  ```
- **Branch**: Create a feature or bugfix branch (e.g., `fix-via-device-error`).
- **Code Review**: Ensure your code adheres to Home Assistant's [coding guidelines](https://developers.home-assistant.io/docs/development_guidelines).
- **Testing**: Confirm that all linting and tests (if implemented) pass before submitting the PR.
- **Documentation**: Update `README.md` or other documentation if your changes introduce new features or modify existing behavior.

## Additional Guidelines

- **Context Exploration**: When making changes, review related files (e.g., `coordinator.py` for API logic, `const.py` for constants) to understand dependencies.
- **Migration Notes**: The integration is compatible with Home Assistant 2025.x.x. Ensure changes maintain compatibility, especially with upcoming changes (e.g., `via_device` removal in 2025.12.0).
- **Documentation**: Add or update inline comments in the code for clarity. If adding new features, update `README.md` or create a new section in the GitHub wiki.
- **Issue Reporting**: Report bugs or feature requests at [https://github.com/Ludy87/ipv64/issues](https://github.com/Ludy87/ipv64/issues).

## Contact

For questions or support, contact the maintainer:

- **Ludy87** ([GitHub](https://github.com/Ludy87))

Thank you for contributing to the `ipv64` integration!
