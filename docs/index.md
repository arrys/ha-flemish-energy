# Flemish Energy

```{toctree}
:hidden:

changelog
```

Flemish Energy imports your published Mijn Fluvius usage and combines it with the current ENGIE Belgium rate in Home Assistant. The **Energy & Costs** dashboard appears automatically after you save your first verified estimate.

## Install

Use **Settings → Marketplace → Add from link** and enter the [Flemish Energy GitHub mirror](https://github.com/arrys/ha-flemish-energy). The [GitLab project](https://git.rys.app/arrys/ha-flemish-energy) hosts the source and release ZIPs. For a manual install, extract the ZIP into the Home Assistant configuration directory so that `custom_components/flemish_energy/manifest.json` is present, then restart Home Assistant. Home Assistant **2026.11 or later** is required.

## Connect accounts and create an estimate

1. Open **Settings → Devices & services → Add integration → Flemish Energy → Connect a Mijn Fluvius meter**. Use a personal Mijn Fluvius login with an email address and password. In Mijn Fluvius, look under **Verbruik → Mijn EAN-lijst** for the 18-digit EAN. Enter the physical meter's serial number and choose electricity or gas.
2. After the wizard verifies that the portal returns readings, select **Save meter and import history**. Add gas and electricity as separate meters. Home Assistant stores the Fluvius login in its local integration configuration for recurring imports.
3. Use the wizard's ENGIE setup link if necessary. This opens Home Assistant's built-in [ENGIE Belgium](https://www.home-assistant.io/integrations/engie_be/) integration, where you enter your dedicated ENGIE login and verification code.
4. Open **Flemish Energy → Check sources and set up an estimate**. Wait for the first meter import, then choose a historical statistic and its corresponding ENGIE contract rate. Review the test result and select **Save estimate**.
5. Open **Energy & Costs** in the sidebar. Adding another estimate adds another usage chart. The charts use the selected Recorder statistics directly.

## Read the dashboard

Each chart shows up to 30 days of published usage for one configured statistic. Choose either the electricity total or its individual tariff streams when setting up estimates. For grid export, choose the injection compensation rate. For dual-rate electricity, match each statistic to the corresponding rate and tariff schedule.

An estimate multiplies the available readings for the displayed Brussels calendar date by the current contract rate. The default date is three days ago to allow time for publication. Estimates refresh every 15 minutes and can change when new readings arrive or the rate changes. Historical billing, dynamic interval pricing, fixed fees, and capacity charges are outside the calculation.

The integration manages the sidebar entry while at least one estimate is loaded. The default path is `/flemish-energy/energy`. If that path is in use, it selects an available suffix. Add another dashboard separately if you want to customize the layout.

## Troubleshoot

| Symptom | What to check |
| --- | --- |
| The wizard reports an account needs setup or repair | Open its integration in **Settings → Devices & services** and complete setup or reauthentication. |
| No Fluvius statistics appear | Check the Flemish Energy meter entry and confirm the consumption readings are visible in Mijn Fluvius. |
| The test finds no readings for the selected day | Choose an older day and compare against Mijn Fluvius. |
| The rate is unavailable | Check the ENGIE integration and select an active contract sensor in EUR/kWh. Signing into the Smart App with the dedicated integration user can end its session. |
| Energy & Costs is missing | Check that at least one Flemish Energy entry is loaded and refresh the browser sidebar. |

To change the day offset or choose a renamed source entity, remove and recreate the corresponding estimate. Existing estimates can still read previously configured Fluvius statistics. If switching to bundled Fluvius import, verify a new estimate against the new meter source before removing the old entry.
