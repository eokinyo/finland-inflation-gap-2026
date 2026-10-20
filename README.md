# Finland's inflation gap, September 2026

Charts for the article "Finland's inflation cushion: 2.7% against the euro area's 3.8% in September".
Every number is downloaded by `make_charts.py` from the official APIs. No figure is typed by hand.

## Run

    python -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python make_charts.py

The script saves the raw API responses and tidy CSV files in `data/` and the charts in `output/`. It stops
with an error if the September 2026 values differ from the releases (Finland HICP 2.7, euro area HICP 3.8,
Finland CPI 2.5).

## Outputs

1. `output/chart1_finland_vs_euro_area.png`: Finland and euro area harmonised inflation, Jan 2024 to Sept 2026.
2. `output/chart2_member_states_sept2026.png`: the 21 euro area members and the euro area, September 2026.
3. `output/chart3_finland_cpi_vs_hicp.png`: Finland's national CPI and HICP, Jan 2024 to Sept 2026.

## Sources

- Eurostat, HICP monthly data, annual rate of change, all items (API dataset `prc_hicp_minr`, updated
  16 Oct 2026). Release: "Annual inflation up to 3.8% in the euro area", 16 Oct 2026,
  https://ec.europa.eu/eurostat/en/web/products-euro-indicators/w/2-16102026-ap
- Statistics Finland, Consumer Price Index (2025=100), monthly data, table 15b5, and HICP (2025=100),
  monthly data, table 15b7. Release: Consumer price index, September 2026, 14 Oct 2026,
  https://stat.fi/en/publication/cmfb09pic2wkf07us5svtrg0p

Data downloaded on 20 Oct 2026.

## Licence

Code: MIT. Data: Eurostat and Statistics Finland (CC BY 4.0), reused under their terms.
