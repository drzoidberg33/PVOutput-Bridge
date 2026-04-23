# PVOutput Bridge

A Home Assistant integration that reads your existing PV-related entities and
uploads live status data to [pvoutput.org](https://pvoutput.org).

> **Community integration — not affiliated with, endorsed by, or supported by
> PVOutput.org.** This project is maintained independently by the Home
> Assistant community. For issues with this integration, please use the GitHub
> issue tracker; do not contact PVOutput.org support.

## What it does

- Reads power/energy/temperature/voltage from entities you already have in
  Home Assistant (inverter integrations, energy meters, etc.).
- Uploads status data to your PVOutput system on a 5, 10, or 15 minute
  schedule using the PVOutput API.
- Configured entirely through the Home Assistant UI — no YAML.

## Requirements

- Home Assistant 2024.12 or newer.
- A [PVOutput.org](https://pvoutput.org) account with a registered system,
  API key, and System ID.
- At least one entity in Home Assistant representing PV power generation.

## Installation

### Step 1: Add the Custom Repository in HACS

1. In your Home Assistant sidebar, select the **HACS** icon.
2. Click the **three-dot menu (⋮)** in the top-right corner of the HACS dashboard.
3. Select **Custom repositories**.
4. In the dialog that appears:
   - **Repository URL:** `https://github.com/drzoidberg33/PVOutput-Bridge`
   - **Type:** Select `Integration` from the dropdown
5. Click **Add**.
6. Close the dialog once the repository has been added.

---

### Step 2: Install the Integration

1. In the HACS dashboard, search for **PVOutput Bridge** using the search bar at the top.
2. Click on **PVOutput Bridge** in the results to open its details page.
3. Click the **Download** button in the bottom-right corner.
4. When prompted, confirm by clicking **Download** again.

---

### Step 3: Restart Home Assistant

After the download completes, you **must restart Home Assistant** for the integration to be loaded:

1. Go to **Settings → System → Restart**.
2. Click **Restart** and wait for Home Assistant to come back online.

---

### Step 4: Add the Integration

1. Go to **Settings → Devices & Services**.
2. Click **+ Add Integration** in the bottom-right corner.
3. Search for **PVOutput Bridge**.
4. Follow the on-screen configuration steps to complete the setup.


## Status

Early development. See the task plan in the repository for current progress.
