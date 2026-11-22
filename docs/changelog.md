# Release notes

## Unreleased

- Shows estimated import cost and export compensation in euros, split by peak and off-peak tariff for the same published day.

## v0.4.5

- Fixes the dashboard load error when looking up the related electricity statistics in Home Assistant Recorder.

## v0.4.4

- Combines import and export for each Fluvius electricity meter in a chart with day and night tariff series, alongside matching current ENGIE rates.

## v0.4.3

- Separates Fluvius sign-in, meter setup, and energy provider selection. New estimates are named **Energy** by default.
- Links a Pidpa cumulative water sensor and shows its meter reading and daily usage in Energy & Costs.

## v0.4.2

- Adds a step-by-step Fluvius-first setup with an **Add another meter** option that reuses the account login before continuing to ENGIE.

## v0.4.1

- Continues from a saved Fluvius meter to the estimate checks.
- Discovers available ENGIE rates and finds the latest usable Fluvius day through Home Assistant.
- Shows the source names in the preview and preserves fixed offsets for existing estimates.

## v0.4.0

- Imports Mijn Fluvius meter history directly from Flemish Energy, with a guided connection test and reauthentication.
- Adds integration icons and a wordmark for Home Assistant.
- Builds the GitLab Pages documentation with Sphinx, MyST, and the Read the Docs theme.

## v0.3.0

- Adds the Energy & Costs dashboard automatically after the first verified estimate is saved.
- Shows 30-day charts for the selected Fluvius statistics alongside current-rate estimates.
- Includes an installation guide and troubleshooting, a GitLab Pages build, and a tagged release pipeline with a downloadable integration archive.
