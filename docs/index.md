# Flemish Energy

Flemish Energy brings your published Mijn Fluvius usage and current ENGIE Belgium rate together in Home Assistant. The **Energy & Costs** dashboard appears automatically after you save your first verified meter and rate.

## Install

1. Use Home Assistant **2026.11 or later** with Recorder and Lovelace enabled. Extract the integration archive into the Home Assistant configuration directory so that `custom_components/flemish_energy/manifest.json` is present. Restart Home Assistant.
2. Go to **Settings → Devices & services → Add integration → Flemish Energy**.
3. Follow the wizard's links if you need to set up [ENGIE Belgium](https://www.home-assistant.io/integrations/engie_be/) or [Fluvius Energy](https://github.com/sander110419/Fluvius-home-assistant). ENGIE needs a dedicated login and a verification code. Fluvius needs your Mijn Fluvius login, meter EAN, and serial number. Select kWh for gas estimates.
4. Wait for meter readings to appear in Recorder, then continue. Choose a historical statistic and the corresponding contract rate. Check the test result and select **Save estimate**.
5. Open **Energy & Costs** in the sidebar. Adding another estimate adds another usage chart. The managed dashboard uses the selected statistics directly, so it works without configuring the built-in Energy dashboard.

## Read the dashboard

Each chart shows up to 30 days of published usage for one configured statistic. Choose either the electricity total or its individual tariff streams when setting up estimates. For grid export, choose the injection compensation rate. For dual-rate electricity, match each statistic to the corresponding rate and tariff schedule.

An estimate multiplies the available readings for the displayed Brussels calendar date by the current contract rate. The default date is three days ago to allow time for publication. Estimates refresh every 15 minutes and can change when new readings arrive or the rate changes. Historical billing, dynamic interval pricing, fixed fees, and capacity charges are outside the calculation.

The integration manages the sidebar entry while at least one estimate is loaded. The default path is `/flemish-energy/energy`. If that path is in use, it selects an available suffix. Add another dashboard separately if you want to customize the layout.

## Troubleshoot

| Symptom | What to check |
| --- | --- |
| The wizard reports an account needs setup or repair | Open its integration in **Settings → Devices & services** and complete setup or reauthentication. |
| No Fluvius statistics appear | Check the first import and its meter permissions. For gas, check that the imported statistic uses kWh. |
| The test finds no readings for the selected day | Choose an older day and compare against Mijn Fluvius. |
| The rate is unavailable | Check the ENGIE integration and select an active contract sensor in EUR/kWh. Signing into the Smart App with the dedicated integration user can end its session. |
| Energy & Costs is missing | Check that at least one Flemish Energy entry is loaded and refresh the browser sidebar. |

To change the day offset or choose a renamed source entity, remove and recreate the corresponding estimate. Authentication and meter imports are handled by the provider integrations.
