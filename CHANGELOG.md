# Changelog

## v0.0.3 — 2026-08-30

- Add OAuth reauthentication for expired or revoked Beatbot credentials.
- Reject reauthentication with a different Beatbot account.
- Preserve existing credentials when resource API validation fails.
- Update and reload the existing Home Assistant config entry after successful reauthentication.
- Correct repository documentation and issue-tracker URLs.
- Add Apache-2.0 licensing and attribution for public distribution.
- Validate the complete suite: 125 tests passed on Home Assistant 2026.2.3.

## v0.0.2

- Initial custom-integration implementation with OAuth2/PKCE, cloud push updates, reconciliation polling, vacuum controls, sensors, binary sensors, selectors, switches, translations, and tests.
