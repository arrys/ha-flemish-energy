# Flemish Energy

```{toctree}
:hidden:

changelog
```

Flemish Energy imports your published Mijn Fluvius usage and combines it with the current ENGIE Belgium rate in Home Assistant. The **Energy & Costs** dashboard appears automatically after you save your first verified estimate.

## Install

Use **Settings → Marketplace → Add from link** and enter the [Flemish Energy GitHub mirror](https://github.com/arrys/ha-flemish-energy). The [GitLab project](https://git.rys.app/arrys/ha-flemish-energy) hosts the source and release ZIPs. For a manual install, extract the ZIP into the Home Assistant configuration directory so that `custom_components/flemish_energy/manifest.json` is present, then restart Home Assistant. Home Assistant **2026.11 or later** is required.

## Connect accounts and create an estimate

1. Open **Settings → Devices & services → Add integration → Flemish Energy**. Sign in with your personal Mijn Fluvius email and password. The wizard checks the login before asking for a meter.
2. Add your first meter. Find its 18-digit EAN under **Verbruik → Mijn EAN-lijst** in Mijn Fluvius, then enter its serial number and choose electricity or gas. Select **Save meter and import history**, then **Add another meter** as many times as needed. Home Assistant stores the login locally for recurring imports.

   To track water, choose **Add a Pidpa water meter** before moving on to the energy provider. You can also add it later from the Flemish Energy setup menu.
3. Select **Done with meters → Choose energy provider** and choose **ENGIE Belgium**. If needed, use the link to Home Assistant's built-in [ENGIE Belgium](https://www.home-assistant.io/integrations/engie_be/) setup for your dedicated login and verification code.
4. Return to the wizard and recheck the sources. Once the meters have imported readings, choose a historical statistic and its corresponding ENGIE contract rate. The estimate defaults to **Energy** and can be renamed in the wizard. Review the test result and select **Save estimate**. To add another meter later, reopen Flemish Energy and choose **Add a meter to an existing Fluvius account**.
5. Open **Energy & Costs** in the sidebar. Adding another estimate adds another usage chart. The charts use the selected Recorder statistics directly.

## Read the dashboard

### Pidpa water

Choose an available Home Assistant sensor that reports cumulative water volume in litres or cubic metres. For a digital Pidpa meter linked to the electricity meter, use a reader that can expose water data from the activated P1 port in Home Assistant. See [Pidpa’s guidance on digital meters](https://www.pidpa.be/veelgestelde-vragen).

The dashboard shows the current meter reading and daily usage from Home Assistant’s Recorder. Home Assistant needs time to build history for a newly added sensor. This setup reads your local Home Assistant sensor and does not import past readings or bills from Mijn Pidpa. If the source entity ID changes, remove the Pidpa entry and add it again with the new sensor.

### Electricity and gas

Energy & Costs combines electricity import and export in one daily chart per configured Fluvius electricity meter. The chart separates high and low tariff readings when both are available for a direction, or shows that direction’s total when a full split is unavailable. The current ENGIE tariff panel uses the contract linked to the estimate when it matches the meter’s EAN. These are current prices in EUR/kWh.

Each chart shows up to 30 days of published usage for one configured statistic. Choose either the electricity total or its individual tariff streams when setting up estimates. For grid export, choose the injection compensation rate. For dual-rate electricity, match each statistic to the corresponding rate and tariff schedule.

An estimate multiplies the available readings for the displayed Brussels calendar date by the current contract rate. By default it follows the newest past day with usable published readings in the last 14 days. Enter a fixed day offset in the wizard to use that instead. Estimates refresh every 15 minutes and can change when new readings arrive or the rate changes. Historical billing, dynamic interval pricing, fixed fees, and capacity charges are outside the calculation.

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
