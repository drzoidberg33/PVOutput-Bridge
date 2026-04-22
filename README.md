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

Installation instructions will be added once the integration is published to
HACS.

## Status

Early development. See the task plan in the repository for current progress.
