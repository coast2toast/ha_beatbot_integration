# Changelog

## Unreleased

- Reach the self-assessed Silver Home Assistant Integration Quality Scale tier.
- Add explicit entity-platform parallel-update limits.
- Coalesce partial cloud state-service outage and recovery logging while
  tracking freshness per device and marking stale runtime entities unavailable.
- Raise translated validation errors for unsupported work-mode selections.
- Surface translated control-authentication failures and start reauthentication.
- Expand behavior tests so every non-empty integration module exceeds 95
  percent statement coverage, with 99.74 percent aggregate coverage, and
  enforce both thresholds in GitHub Actions.
- Document OAuth-derived installation and configuration parameters.

## 2026.08.31

- Add OAuth reauthentication for expired or revoked Beatbot credentials.
- Reject reauthentication with a different Beatbot account.
- Preserve existing credentials when resource API validation fails.
- Update and reload the existing Home Assistant config entry after successful reauthentication.
- Correct repository documentation and issue-tracker URLs.
- Add Apache-2.0 licensing and attribution for public distribution.
- Validate the complete suite: 125 tests passed on Home Assistant 2026.2.3.
- Add automated HACS Action and Home Assistant hassfest validation.
- Document HACS custom-repository readiness and the self-assessed Bronze
  Integration Quality Scale tier.

## v0.0.2

- Initial custom-integration implementation with OAuth2/PKCE, cloud push updates, reconciliation polling, vacuum controls, sensors, binary sensors, selectors, switches, translations, and tests.
