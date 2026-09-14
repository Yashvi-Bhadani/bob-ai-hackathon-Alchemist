# Problem Statement

## Background

Semiconductor manufacturing (fab operations) runs on highly complex, capital-intensive equipment that processes silicon wafers through dozens of sequential steps. Each step must be completed in order — lithography, etch, deposition, planarisation, metal fill, inspection. A single step that becomes saturated in throughput creates a **manufacturing bottleneck** that backs up every step behind it.

At the same time, fabs depend on a global supply chain for speciality materials — photoresists, dopant gases, sputter targets, and precision chemicals — that are often sourced from one or two suppliers worldwide. A logistics disruption, geopolitical event, or export-control change can halt material supply and shut down affected tools within days.

## The Problem

Fab operations managers and supply-chain engineers currently work from **separate, disconnected tools**:

- MES (Manufacturing Execution Systems) track tool utilisation and WIP queue depth
- ERP systems track inventory and purchase orders
- Supply chain analysts separately track supplier concentration and risk

**There is no system that simultaneously:**
1. Identifies which tools are bottlenecks and why (using quantified scores)
2. Simulates what happens if a critical tool goes down for N hours
3. Traces which downstream process steps are affected
4. Identifies which materials are at risk of supply disruption
5. Combines manufacturing and supply-chain risk into a single actionable score
6. Recommends specific, prioritised mitigations
7. Explains all of this in natural language for decision-makers

The result: when a critical tool like an EUV lithography scanner fails, operations managers scramble across multiple systems to understand impact — typically 30–90 minutes of manual analysis before a decision can be made.

## Who is Affected

- **Fab Operations Managers** who need rapid situational awareness when bottlenecks or outages occur
- **Supply Chain Analysts** who monitor material risk but lack context about which materials are production-critical right now
- **Process Engineers** who need to understand downstream propagation of bottleneck delays
- **Executive / Production Planning** who need combined risk scores to authorise response actions (overtime, emergency procurement, lot rerouting)

## Why It Matters

A single EUV scanner running at 94% utilisation with 38 lots queued represents millions of dollars per day of potential output held in queue. An 8-hour unplanned outage on such a tool — combined with 5-day inventory coverage for the required photoresist and a 70% single-supplier dependency — creates a compounding risk scenario that can delay wafer starts by days or weeks.

The semiconductor industry operates on extremely tight delivery windows; even a 2-day cycle-time increase on a high-volume product line can result in missed customer commitments worth tens of millions of dollars.

## Why Existing Solutions Fall Short

- **MES dashboards** show raw utilisation numbers but do not compute bottleneck scores, simulate outages, or connect to supply-chain data
- **ERP inventory reports** show stock levels but do not compute coverage days in risk-tier terms or connect to manufacturing bottleneck context
- **Analyst spreadsheets** can do ad hoc calculations but require 30+ minutes per scenario and are not real-time
- **No tool combines manufacturing risk and supply chain risk** into a single decision-ready score with automated recommendations

This is the gap the Fab Bottleneck & Supply Chain Risk Advisor fills.
