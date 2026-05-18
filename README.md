# RCDef — Composite Defensive Analytics

A non-commercial baseball defensive analytics tool combining OAA, FRV, DRS, and original components into a single runs-above-average metric.

## Stats

| Metric | Description |
|--------|-------------|
| **RCDef** | Composite defensive runs above average |
| **RCDef+** | Position-specific percentile (0–100) |
| **CR** | Conversion Runs |
| **ARS** | Attempt Range Score (with neighbor adjustment) |
| **RRAA** | Receiving Runs Above Average (1B only) |
| **BAP** | Baserunner Advancement Prevention |
| **ARM** | Arm Runs |
| **SC** | Stadium Correction |

## Original Components

**RRAA (Receiving Runs Above Average)** — First base receiving quality has never been cleanly measured in a public tool. RRAA uses raw Statcast throw data to credit first basemen for dirt ball handling, wide throw receiving, and stretch plays.

**BAP (Baserunner Advancement Prevention)** — Measures suppression of extra-base advancement through positioning speed and deterrence, separate from direct arm value.

**Neighbor Adjustment** — Hybrid model detecting when neighboring fielders are suppressing or inflating a fielder's Attempt Range score, with a 30%-capped credit adjustment for suppression and a transparency flag for vacuum inflation.

## Data Sources

- **Baseball Savant / Statcast** — OAA, FRV, Sprint Speed, Arm Data, Framing (public)
- **Baseball Reference** — DRS display (non-commercial attribution, © Sports Info Solutions)
- **Original calculation** — CR, ARS, RRAA, BAP from raw Statcast data

## Deployment

### Local
```bash
pip install -r requirements.txt
streamlit run rcdef_app.py
```

### Streamlit Community Cloud
1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Deploy from `rcdef_app.py`

Data refreshes automatically via GitHub Actions (nightly during season, weekly offseason).

## Methodology

Full methodology is documented in the app's Methodology tab, including:
- Component calculations
- Neighbor adjustment logic
- Stadium correction factors
- Known limitations
- Data source attribution

## Attribution

DRS data © Sports Info Solutions / Baseball Reference  
Non-commercial use only  
All original methodology published openly

## Scope

- Seasons: 2025–2026 (expandable to full Statcast era 2015+)
- Regular season only
- Minimum 300 innings for full leaderboard
- Shift-era adjustment applied (2023 boundary)
