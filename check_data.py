"""Check the charted September 2026 values against the saved data and the official APIs.

  python check_data.py            # re-fetch from Eurostat and Statistics Finland, compare with data/
  python check_data.py --offline  # check the saved files in data/ only

Exits with status 1 and a message for every mismatch. Nothing in data/ is overwritten.
"""
import csv, json, pathlib, sys

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"
END = "2026-09"
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr"
STATFIN = "https://statfin.stat.fi/PxWeb/api/v1/en/StatFin/khi/"
EA_MEMBERS = ["AT", "BE", "BG", "CY", "DE", "EE", "EL", "ES", "FI", "FR", "HR", "IE", "IT", "LT", "LU",
              "LV", "MT", "NL", "PT", "SI", "SK"]
# Values charted in the article (September 2026 releases)
EXPECTED = {"Finland HICP": 2.7, "Euro area HICP": 3.8, "Finland CPI": 2.5,
            "Finland HICP (Statistics Finland)": 2.7, "Malta HICP": 2.4}
EXPECTED_RANK = 2  # Finland second lowest of 21 members, after Malta


def eurostat_get(d):
    dims, sizes = d["id"], d["size"]
    idx = {k: d["dimension"][k]["category"]["index"] for k in dims}
    def get(**sel):
        pos = 0
        for k, s in zip(dims, sizes):
            pos = pos * s + (idx[k][sel[k]] if k in sel else 0)
        return d["value"].get(str(pos))
    return get


def statfin_last(d):
    t = d["dimension"]["timeperiod_m"]["category"]["index"]
    return d["value"][t[END.replace("-", "M")]]


def values_from_json(fi_ea, members, s15b5, s15b7):
    sel = dict(time=END, unit="RCH_A", coicop18="TOTAL", freq="M")
    ts, mg = eurostat_get(fi_ea), eurostat_get(members)
    return {"Finland HICP": ts(geo="FI", **sel), "Euro area HICP": ts(geo="EA", **sel),
            "Finland CPI": statfin_last(s15b5), "Finland HICP (Statistics Finland)": statfin_last(s15b7),
            "members": {g: mg(geo=g, **sel) for g in EA_MEMBERS}}


def values_from_csv():
    rows = lambda n: list(csv.DictReader(open(DATA / n)))
    fe = {r["month"]: r for r in rows("hicp_fi_ea.csv")}[END]
    sf = {r["month"]: r for r in rows("statfin_cpi_hicp.csv")}[END]
    mem = {r["geo"]: float(r["hicp_annual_rate"]) for r in rows("hicp_members_2026_09.csv")}
    return {"Finland HICP": float(fe["finland_hicp"]), "Euro area HICP": float(fe["euro_area_hicp"]),
            "Finland CPI": float(sf["cpi_annual_change"]),
            "Finland HICP (Statistics Finland)": float(sf["hicp_annual_change"]),
            "members": {g: mem.get(g) for g in EA_MEMBERS}}


def fetch():
    import requests
    base = {"format": "JSON", "lang": "EN", "unit": "RCH_A", "coicop18": "TOTAL", "freq": "M"}
    def es(p):
        r = requests.get(EUROSTAT, params=dict(base, **p), timeout=120); r.raise_for_status(); return r.json()
    def sf(table, content):
        q = {"query": [{"code": "coicop_46_20231201", "selection": {"filter": "item", "values": ["SSS"]}},
                       {"code": "contentscode", "selection": {"filter": "item", "values": [content]}},
                       {"code": "timeperiod_m", "selection": {"filter": "item", "values": [END.replace("-", "M")]}}],
             "response": {"format": "json-stat2"}}
        r = requests.post(STATFIN + table, json=q, timeout=120); r.raise_for_status(); return r.json()
    return values_from_json(es({"geo": ["FI", "EA"], "time": END}), es({"geo": EA_MEMBERS, "time": END}),
                            sf("15b5.px", "vm_khi"), sf("15b7.px", "vm_ykhi"))


def check(label, v):
    errs = []
    for k, want in EXPECTED.items():
        got = v["members"].get("MT") if k == "Malta HICP" else v[k]
        if got != want:
            errs.append(f"{label}: {k} is {got}, article charts {want}")
    mem = v["members"]
    if None in mem.values():
        errs.append(f"{label}: missing member values {[g for g, x in mem.items() if x is None]}")
    else:
        lower = sorted(g for g, x in mem.items() if x < mem["FI"])
        tied = sorted(g for g, x in mem.items() if x == mem["FI"] and g != "FI")
        if len(mem) != 21 or lower != ["MT"] or tied:
            errs.append(f"{label}: Finland is not second lowest of 21 after Malta "
                        f"(members {len(mem)}, lower {lower}, tied {tied})")
    print(f"{label}: " + ("OK " if not errs else "FAIL ") +
          ", ".join(f"{k} {v['members']['MT'] if k == 'Malta HICP' else v[k]}" for k in EXPECTED))
    return errs


def main():
    offline = "--offline" in sys.argv[1:]
    load = lambda n: json.loads((DATA / n).read_text())
    saved_json = values_from_json(load("eurostat_fi_ea.json"), load("eurostat_members_sept2026.json"),
                                  load("statfin_15b5.json"), load("statfin_15b7.json"))
    errs = check("saved JSON", saved_json) + check("saved CSV", values_from_csv())
    if not offline:
        try:
            live = fetch()
        except Exception as e:
            print(f"ERROR: could not fetch from the APIs: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(2)
        errs += check("live APIs", live)
        if live != saved_json:
            errs.append("live APIs differ from saved data/ (data may have been revised; rerun make_charts.py)")
    for e in errs:
        print("MISMATCH:", e, file=sys.stderr)
    if errs:
        sys.exit(1)
    print("All September 2026 values match.")


if __name__ == "__main__":
    main()
