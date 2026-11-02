from analyst.cleaning import clean


def test_rows_kept(raw):
    df, _ = clean(raw)
    assert sorted(df["ride_id"]) == ["A", "D", "F", "I"]


def test_log_counts(raw):
    _, log = clean(raw)
    removed = {s["step"]: s["rows_removed"] for s in log.steps}
    assert removed["doublons ride_id"] == 1
    assert removed["dates illisibles"] == 1
    assert removed["durée <= 0"] == 1
    assert removed["durée < 60 s"] == 1
    assert removed["durée > 24 h"] == 1
    assert removed["station d'arrivée manquante"] == 1
    assert sum(removed.values()) == len(raw) - 4
    fixed = next(s for s in log.steps if s["step"] == "id station d'arrivée reconstitué")
    assert fixed["values_changed"] == 1


def test_documented_rules_have_source(raw):
    _, log = clean(raw)
    for step in ("durée < 60 s", "durée > 24 h"):
        s = next(x for x in log.steps if x["step"] == step)
        assert "citibikenyc.com" in s["source"]


def test_labels_and_derived_columns(clean_df):
    d = clean_df.set_index("ride_id")
    assert d.loc["D", "rideable_type"] == "classic_bike"
    assert d.loc["D", "member_casual"] == "casual"
    assert d.loc["D", "end_station_id"] == "JC005"  # retrouvé par le nom
    assert d.loc["A", "start_city"] == "Jersey City" and d.loc["A", "end_city"] == "Hoboken"
    assert d.loc["F", "end_city"] == "New York"
    assert d.loc["A", "duration_min"] == 10
    assert bool(d.loc["I", "round_trip"]) and not bool(d.loc["A", "round_trip"])


def test_raw_not_modified(raw):
    before = raw.copy()
    clean(raw)
    assert raw.equals(before)
