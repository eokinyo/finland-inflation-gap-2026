"""Charts for the W44 article on Finland's inflation gap (September 2026).

Downloads every number from the official APIs (no hand-typed figures), saves the raw
responses and tidy CSVs in data/, and writes three PNG charts to output/.
Run: python make_charts.py
"""
import csv, json, pathlib
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt

ROOT = pathlib.Path(__file__).parent
DATA, OUT = ROOT / "data", ROOT / "output"
START, END = "2024-01", "2026-09"
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr"
STATFIN = "https://statfin.stat.fi/PxWeb/api/v1/en/StatFin/khi/"
# Euro area members in 2026 (21, Bulgaria joined on 1 Jan 2026)
EA_MEMBERS = ["AT", "BE", "BG", "CY", "DE", "EE", "EL", "ES", "FI", "FR", "HR", "IE", "IT", "LT", "LU",
              "LV", "MT", "NL", "PT", "SI", "SK"]
NAMES = dict(AT="Austria", BE="Belgium", BG="Bulgaria", CY="Cyprus", DE="Germany", EE="Estonia", EL="Greece",
             ES="Spain", FI="Finland", FR="France", HR="Croatia", IE="Ireland", IT="Italy", LT="Lithuania",
             LU="Luxembourg", LV="Latvia", MT="Malta", NL="Netherlands", PT="Portugal", SI="Slovenia",
             SK="Slovakia", EA="Euro area")
FI_BLUE, EA_GREY, ACCENT = "#1f4e9c", "#7f8c8d", "#c0392b"
plt.rcParams.update({"font.size": 15, "axes.titlesize": 20, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})


def months():
    y, m = map(int, START.split("-"))
    out = []
    while f"{y}-{m:02d}" <= END:
        out.append(f"{y}-{m:02d}"); m += 1
        if m == 13: y, m = y + 1, 1
    return out


def eurostat(params, name):
    r = requests.get(EUROSTAT, params=params, timeout=120); r.raise_for_status()
    d = r.json(); (DATA / f"{name}.json").write_text(json.dumps(d, indent=1))
    dims = d["id"]; sizes = d["size"]
    idx = {k: {v: i for i, v in enumerate(sorted(d["dimension"][k]["category"]["index"],
                                                   key=d["dimension"][k]["category"]["index"].get))} for k in dims}
    def get(**sel):
        pos = 0
        for k, s in zip(dims, sizes):
            pos = pos * s + idx[k][sel[k]] if k in sel else pos * s
        return d["value"].get(str(pos))
    return d, get


def statfin(table, content):
    q = {"query": [{"code": "coicop_46_20231201", "selection": {"filter": "item", "values": ["SSS"]}},
                   {"code": "contentscode", "selection": {"filter": "item", "values": [content]}},
                   {"code": "timeperiod_m", "selection": {"filter": "item",
                                                          "values": [m.replace("-", "M") for m in months()]}}],
         "response": {"format": "json-stat2"}}
    r = requests.post(STATFIN + table, json=q, timeout=120); r.raise_for_status()
    d = r.json(); (DATA / f"statfin_{table.split('.')[0]}.json").write_text(json.dumps(d, indent=1))
    t = d["dimension"]["timeperiod_m"]["category"]["index"]
    order = sorted(t, key=t.get)
    return {k.replace("M", "-"): d["value"][i] for i, k in enumerate(order)}


def write_csv(name, header, rows):
    with open(DATA / name, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def caption(fig, text):
    fig.text(0.01, 0.01, text, fontsize=13, color="#555555", ha="left", va="bottom")


def main():
    DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    ms = months()
    base = {"format": "JSON", "lang": "EN", "unit": "RCH_A", "coicop18": "TOTAL", "freq": "M"}
    _, ts = eurostat(dict(base, geo=["FI", "EA"], sinceTimePeriod=START, untilTimePeriod=END), "eurostat_fi_ea")
    fi = [ts(geo="FI", time=m, unit="RCH_A", coicop18="TOTAL", freq="M") for m in ms]
    ea = [ts(geo="EA", time=m, unit="RCH_A", coicop18="TOTAL", freq="M") for m in ms]
    assert None not in fi + ea, "missing Eurostat values"
    write_csv("hicp_fi_ea.csv", ["month", "finland_hicp", "euro_area_hicp"], zip(ms, fi, ea))
    _, ms_get = eurostat(dict(base, geo=EA_MEMBERS + ["EA"], time=END), "eurostat_members_sept2026")
    members = {g: ms_get(geo=g, time=END, unit="RCH_A", coicop18="TOTAL", freq="M") for g in EA_MEMBERS + ["EA"]}
    assert None not in members.values(), "missing member values"
    write_csv("hicp_members_2026_09.csv", ["geo", "name", "hicp_annual_rate"],
              [(g, NAMES[g], v) for g, v in members.items()])
    cpi, hicp_sf = statfin("15b5.px", "vm_khi"), statfin("15b7.px", "vm_ykhi")
    write_csv("statfin_cpi_hicp.csv", ["month", "cpi_annual_change", "hicp_annual_change"],
              [(m, cpi[m], hicp_sf[m]) for m in ms])

    # Done test: September 2026 values must match the releases
    checks = {"Finland HICP": (fi[-1], 2.7), "Euro area HICP": (ea[-1], 3.8), "Finland CPI": (cpi[END], 2.5),
              "Finland HICP (Statistics Finland)": (hicp_sf[END], 2.7)}
    for k, (got, want) in checks.items():
        assert got == want, f"{k}: {got} != release {want}"

    x = [dt.date(int(m[:4]), int(m[5:]), 1) for m in ms]

    # Chart 1
    fig, ax = plt.subplots(figsize=(16, 9), dpi=110)
    ax.plot(x, ea, color=EA_GREY, lw=3.5, label="Euro area")
    ax.plot(x, fi, color=FI_BLUE, lw=3.5, label="Finland")
    ax.annotate("", xy=(x[-1], ea[-1]), xytext=(x[-1], fi[-1]),
                arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=2.5))
    ax.text(x[-1] + dt.timedelta(days=12), (ea[-1] + fi[-1]) / 2,
            f"Gap {ea[-1] - fi[-1]:.1f}\npoints", color=ACCENT, fontsize=16, fontweight="bold", va="center")
    ax.text(x[-1] + dt.timedelta(days=12), ea[-1], f"{ea[-1]:.1f}%", color=EA_GREY, fontsize=15, va="bottom")
    ax.text(x[-1] + dt.timedelta(days=12), fi[-1], f"{fi[-1]:.1f}%", color=FI_BLUE, fontsize=15, va="top")
    ax.set_xlim(x[0], x[-1] + dt.timedelta(days=95))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.axhline(0, color="#cccccc", lw=1)
    ax.set_ylabel("Annual inflation, %"); ax.grid(axis="y", alpha=0.3)
    ax.set_title("Finland's inflation stays below the euro area's", loc="left")
    ax.legend(frameon=False, loc="upper left")
    caption(fig, "Harmonised consumer price inflation, annual rate, Jan 2024 to Sept 2026. "
                 "Source: Eurostat; author's calculations.")
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(OUT / "chart1_finland_vs_euro_area.png"); plt.close(fig)

    # Chart 2
    items = sorted(members.items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(16, 12), dpi=110)
    cols = [FI_BLUE if g == "FI" else (ACCENT if g == "EA" else "#b8c4ce") for g, _ in items]
    ax.barh([NAMES[g] for g, _ in items], [v for _, v in items], color=cols)
    for i, (g, v) in enumerate(items):
        ax.text(v + 0.08, i, f"{v:.1f}", va="center", fontsize=14,
                fontweight="bold" if g in ("FI", "EA") else "normal")
    for lbl in ax.get_yticklabels():
        if lbl.get_text() in ("Finland", "Euro area"):
            lbl.set_fontweight("bold")
    ax.set_xlabel("Annual inflation, %"); ax.grid(axis="x", alpha=0.3)
    ax.set_title("Euro area inflation in September 2026", loc="left")
    caption(fig, "Harmonised consumer price inflation, annual rate, September 2026. "
                 "Source: Eurostat; author's calculations.")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT / "chart2_member_states_sept2026.png"); plt.close(fig)

    # Chart 3
    c, h = [cpi[m] for m in ms], [hicp_sf[m] for m in ms]
    fig, ax = plt.subplots(figsize=(16, 9), dpi=110)
    ax.plot(x, h, color=FI_BLUE, lw=3.5, label="Harmonised index (HICP)")
    ax.plot(x, c, color="#e67e22", lw=3.5, label="National consumer price index (CPI)")
    ax.text(x[-1] + dt.timedelta(days=12), h[-1], f"{h[-1]:.1f}%", color=FI_BLUE, fontsize=15, va="bottom")
    ax.text(x[-1] + dt.timedelta(days=12), c[-1], f"{c[-1]:.1f}%", color="#e67e22", fontsize=15, va="top")
    ax.set_xlim(x[0], x[-1] + dt.timedelta(days=70))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.axhline(0, color="#cccccc", lw=1)
    ax.set_ylabel("Annual change, %"); ax.grid(axis="y", alpha=0.3)
    ax.set_title("Finland: two measures of inflation", loc="left")
    ax.legend(frameon=False, loc="upper left")
    caption(fig, "Annual change, Jan 2024 to Sept 2026. Source: Statistics Finland; author's calculations.")
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(OUT / "chart3_finland_cpi_vs_hicp.png"); plt.close(fig)

    print("Sept 2026:", {k: v[0] for k, v in checks.items()}, "| all match the releases")


if __name__ == "__main__":
    main()
