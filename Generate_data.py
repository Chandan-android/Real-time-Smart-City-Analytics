"""
Generate_data.py — Smart City Bangalore Data Generator
═══════════════════════════════════════════════════════

TWO MODES
─────────
1. HISTORICAL (default, run once)
   Generates 500 000 rows spanning 2010-01-01 → 2025-12-31.
   Output: traffic.csv, energy.csv, pollution.csv
   Used by: Stage-1 EDA (data.ipynb), Stage-2 modelling (model.ipynb)

2. STREAMING (called by producer.py every batch)
   Generates one batch of real-time records starting from 2026-01-01
   or from wherever the last batch left off (stream_state.txt).
   Each call advances the clock by exactly STREAM_INTERVAL_SECONDS
   so timestamps are continuous and evenly spaced — no gaps, no jumps.
   This guarantees smooth dashboard continuity.
   Output: returned as list[dict] to producer.py — never touches disk.

STREAM STATE FILE  (stream_state.txt)
──────────────────────────────────────
Stores the ISO timestamp of the last record generated.
On crash/restart producer reads this file and resumes from the
exact next interval — no duplicate or missing timestamps.
Format (single line): 2026-01-01T08:00:00

TIMESTAMP CONTRACT
──────────────────
• Historical : random within the 2010–2025 window (sorted)
• Streaming  : wall-clock-aligned, one record per area every
               STREAM_INTERVAL_SECONDS (default 10 s per batch).
               The dashboard can thus always display "last N minutes"
               without worrying about out-of-order or missing slots.
"""

import os
import sys
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")

# ══════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════
# ── Historical ────────────────────────────────────────────────────
ROWS            = 500_000
HIST_START      = datetime(2010, 1, 1)
HIST_END        = datetime(2025, 12, 31, 23, 59, 59)

# ── Streaming ─────────────────────────────────────────────────────
STREAM_START          = datetime(2026, 1, 1, 0, 0, 0)   # first record if no state file
STREAM_STATE_FILE     = "stream_state.txt"               # resume file
STREAM_INTERVAL_SECS  = 30                               # seconds between consecutive records
                                                         # must match producer.py DELAY

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

GENERATOR_VERSION = "smartcity_v5.0"

# ══════════════════════════════════════════════════════════════════
#  MASTER DATA  (shared by both modes)
# ══════════════════════════════════════════════════════════════════
areas = [
    "Whitefield","Electronic City","MG Road","Indiranagar","Yelahanka","Silk Board",
    "Hebbal","Marathahalli","BTM Layout","Jayanagar","Rajajinagar","Banashankari",
    "Koramangala","HSR Layout","Bellandur","KR Puram","Malleshwaram","Basavanagudi",
    "Ulsoor","Domlur","Kengeri","Magadi Road","Peenya","Nagawara","Thanisandra",
    "Hennur","Varthur","Sarjapur","Devanahalli","Chandapura","Attibele",
    "Bommanahalli","Kadugodi","Bidadi","Rajarajeshwari Nagar","Yeshwanthpur",
    "Shivajinagar","Majestic","Cubbon Park","JP Nagar","Bannerghatta Road",
]

AREAS_PER_BATCH = len(areas)                                # how many area records per producer batch

area_zone_map = {
    "Whitefield":"East","Electronic City":"South","MG Road":"Central","Indiranagar":"East",
    "Yelahanka":"North","Silk Board":"South","Hebbal":"North","Marathahalli":"East",
    "BTM Layout":"South","Jayanagar":"South","Rajajinagar":"West","Banashankari":"South",
    "Koramangala":"South","HSR Layout":"South","Bellandur":"East","KR Puram":"East",
    "Malleshwaram":"West","Basavanagudi":"South","Ulsoor":"Central","Domlur":"East",
    "Kengeri":"West","Magadi Road":"West","Peenya":"West","Nagawara":"North",
    "Thanisandra":"North","Hennur":"North","Varthur":"East","Sarjapur":"East",
    "Devanahalli":"North","Chandapura":"South","Attibele":"South","Bommanahalli":"South",
    "Kadugodi":"East","Bidadi":"West","Rajarajeshwari Nagar":"West","Yeshwanthpur":"West",
    "Shivajinagar":"Central","Majestic":"Central","Cubbon Park":"Central",
    "JP Nagar":"South","Bannerghatta Road":"South",
}

it_areas          = {"Whitefield","Electronic City","Marathahalli","Bellandur",
                     "HSR Layout","Koramangala","Sarjapur","JP Nagar"}
leisure_areas     = {"MG Road","Indiranagar","Koramangala","Jayanagar","Malleshwaram",
                     "Basavanagudi","Majestic","Cubbon Park","BTM Layout","JP Nagar","HSR Layout"}
industrial_areas  = {"Peenya","Yeshwanthpur","Bommanahalli","Attibele","Bidadi"}

road_type_map = {
    "Highway":   ["Whitefield","Electronic City","Hebbal","Devanahalli","Bidadi","Attibele",
                  "Sarjapur","Chandapura","Kengeri","Varthur"],
    "Main Road": ["Silk Board","Marathahalli","BTM Layout","Koramangala","HSR Layout",
                  "Bellandur","KR Puram","Malleshwaram","Yeshwanthpur","Peenya",
                  "Rajajinagar","Banashankari","Jayanagar","JP Nagar","Yelahanka",
                  "Nagawara","Thanisandra","Hennur","Bommanahalli","Kadugodi"],
    "Street":    ["MG Road","Indiranagar","Basavanagudi","Ulsoor","Domlur",
                  "Magadi Road","Shivajinagar","Majestic","Cubbon Park","Rajarajeshwari Nagar",
                  "Bannerghatta Road"],
}
area_road_type = {}
for road, road_areas in road_type_map.items():
    for a in road_areas:
        area_road_type[a] = road
for a in areas:
    area_road_type.setdefault(a, "Main Road")

weather_conditions = ["Clear","Rain","Cloudy","Heavy Rain"]
events_list        = ["None","Festival","Concert","Political Rally"]

# ── Area weights ──────────────────────────────────────────────────
area_traffic_weight = {
    "Whitefield":1.8,"Electronic City":1.8,"Marathahalli":1.8,"Bellandur":1.7,
    "HSR Layout":1.5,"Koramangala":1.5,"Sarjapur":1.4,"JP Nagar":1.4,
    "Silk Board":1.9,"BTM Layout":1.3,"MG Road":1.3,"Yeshwanthpur":1.4,"Peenya":1.4,
    "Malleshwaram":1.2,"Majestic":1.3,
}
for a in areas: area_traffic_weight.setdefault(a, 1.0)

area_energy_weight = {
    "Whitefield":1.9,"Electronic City":1.9,"Marathahalli":1.7,"Bellandur":1.6,
    "HSR Layout":1.6,"Koramangala":1.6,"Sarjapur":1.5,"JP Nagar":1.6,
    "Peenya":2.0,"Yeshwanthpur":1.8,"Majestic":1.4,"MG Road":1.3,
    "Bommanahalli":1.7,"Attibele":1.6,
}
for a in areas: area_energy_weight.setdefault(a, 1.0)

area_pollution_weight = {
    "Whitefield":1.4,"Electronic City":1.5,"Marathahalli":1.4,"Bellandur":1.4,
    "HSR Layout":1.3,"Koramangala":1.3,"Sarjapur":1.3,"JP Nagar":1.3,
    "Silk Board":1.9,"Peenya":2.0,"Yeshwanthpur":1.8,"KR Puram":1.5,
    "Bommanahalli":1.6,"Majestic":1.5,
}
for a in areas: area_pollution_weight.setdefault(a, 1.0)

# ── Calendar ──────────────────────────────────────────────────────
holiday_multipliers = {(10,24):1.5,(1,26):1.3,(8,15):1.2,(12,31):1.4}

scheduled_events = [
    ("MG Road",      "2026-03-10","2026-03-12",1.6),
    ("Koramangala",  "2026-04-05","2026-04-06",1.5),
    ("Whitefield",   "2026-06-20","2026-06-22",1.4),
    ("MG Road",      "2024-12-20","2024-12-26",1.6),
    ("Koramangala",  "2024-11-10","2024-11-12",1.5),
]

adjacency = {
    "Silk Board":    ["Marathahalli","Bellandur","Koramangala"],
    "Marathahalli":  ["Silk Board","Koramangala","Whitefield"],
    "Whitefield":    ["KR Puram","Varthur","Marathahalli"],
    "Electronic City":["Bommanahalli","Attibele","Koramangala"],
    "Koramangala":   ["HSR Layout","Jayanagar","Marathahalli"],
    "Majestic":      ["Cubbon Park","MG Road","Malleshwaram"],
    "Peenya":        ["Yeshwanthpur","Magadi Road","KR Puram"],
}

# ══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS  (shared)
# ══════════════════════════════════════════════════════════════════
def get_season(month: int) -> str:
    if month in [3,4,5]:      return "Summer"
    if month in [6,7,8,9]:    return "Monsoon"
    return "Winter"

def diurnal_temperature(base_temp: float, hour: int) -> float:
    angle = (hour - 5) * (2 * np.pi / 24)
    return base_temp + 4 * np.sin(angle)

def rush_hour_multiplier(hour: int, is_weekend: bool, area: str) -> float:
    if is_weekend:
        if area in leisure_areas:
            return 1.6 + 0.4 * np.sin((hour-12)*np.pi/8) if 12<=hour<=20 else 0.5
        return 0.6 if 10<=hour<=18 else 0.3
    if 8<=hour<=10:  return 2.5 + 0.5*np.sin((hour-8)*np.pi/2)
    if 17<=hour<=20: return 2.8 + 0.4*np.sin((hour-17)*np.pi/3)
    if 11<=hour<=16: return 1.1
    if 6<=hour<=7:   return 1.4
    return 0.25

def solar_renewable(hour: int) -> float:
    if 6<=hour<=18: return max(0, 45*np.sin((hour-6)*np.pi/12))
    return random.uniform(0, 3)

def neighbor_mean(metric_dict: dict, area: str) -> float:
    neigh = adjacency.get(area, [])
    if not neigh: return 0.0
    vals = [metric_dict.get(n, 0.0) for n in neigh]
    return float(np.mean(vals)) if vals else 0.0

def date_in_range(dt: datetime, start_str: str, end_str: str) -> bool:
    s = datetime.fromisoformat(start_str)
    e = datetime.fromisoformat(end_str) + timedelta(days=1) - timedelta(seconds=1)
    return s <= dt <= e

# ══════════════════════════════════════════════════════════════════
#  PER-AREA STATE  (shared by both modes)
#  For streaming, state persists across calls inside this module.
# ══════════════════════════════════════════════════════════════════
prev_weather      = {a: "Clear"  for a in areas}
prev_energy       = {a: 4000.0   for a in areas}
prev_aqi          = {a: 100      for a in areas}
prev_vehicles     = {a: 0.0      for a in areas}
accident_duration = {a: 0        for a in areas}
event_active      = {a: 0        for a in areas}
event_duration    = {a: 0        for a in areas}
outage_counter    = {a: 0        for a in areas}
drift_counter     = {a: 0        for a in areas}
drift_factor      = {a: 1.0      for a in areas}

# ══════════════════════════════════════════════════════════════════
#  STREAM STATE  — read / write / advance
# ══════════════════════════════════════════════════════════════════
def _read_stream_state() -> datetime:
    """
    Read the last-emitted timestamp from stream_state.txt.
    If the file doesn't exist (first run), return STREAM_START.
    The next batch will begin one STREAM_INTERVAL_SECS after this value,
    guaranteeing no duplicate timestamps on restart.
    """
    if os.path.exists(STREAM_STATE_FILE):
        try:
            with open(STREAM_STATE_FILE, "r") as f:
                ts_str = f.read().strip()
            ts = datetime.fromisoformat(ts_str)
            return ts + timedelta(seconds=STREAM_INTERVAL_SECS)  # resume AFTER last emitted
        except Exception:
            pass  # corrupt file — reset to STREAM_START
    return STREAM_START

def _write_stream_state(last_ts: datetime) -> None:
    """Persist the timestamp of the most recently emitted record."""
    with open(STREAM_STATE_FILE, "w") as f:
        f.write(last_ts.isoformat())

# ══════════════════════════════════════════════════════════════════
#  CORE RECORD GENERATOR  (called by both historical and streaming)
# ══════════════════════════════════════════════════════════════════
def _generate_record(ts: datetime, area: str) -> dict:
    """
    Generate a single correlated (traffic, energy, pollution) record
    for the given timestamp and area.

    Returns a dict with three keys:
        "traffic"   → dict
        "energy"    → dict
        "pollution" → dict

    All three share the same timestamp and area so Spark can join them.
    """
    hour       = ts.hour
    month      = ts.month
    year       = ts.year
    season     = get_season(month)
    is_weekend = int(ts.weekday() >= 5)
    zone       = area_zone_map.get(area, "Central")
    is_it_hub  = 1 if area in it_areas else 0

    # Growth factor — Bangalore's 2% YoY increase, anchored to 2010
    years_passed  = max(0, year - 2010)
    growth_factor = 1.02 ** years_passed

    # ── WEATHER ───────────────────────────────────────────────────
    if random.random() < 0.72:
        weather = prev_weather[area]
    else:
        if season == "Monsoon":
            weather = random.choices(
                ["Rain","Heavy Rain","Cloudy","Clear"],
                weights=[0.38,0.28,0.22,0.12])[0]
        elif season == "Summer":
            weather = random.choices(
                ["Clear","Cloudy","Rain","Heavy Rain"],
                weights=[0.60,0.28,0.10,0.02])[0]
        else:
            weather = random.choices(
                ["Clear","Cloudy","Rain","Heavy Rain"],
                weights=[0.50,0.30,0.15,0.05])[0]
    prev_weather[area] = weather

    # ── TEMPERATURE & HUMIDITY ────────────────────────────────────
    seasonal_base = 32 if season=="Summer" else 24 if season=="Winter" else 27
    base_temp   = float(np.random.normal(seasonal_base, 2))
    temperature = diurnal_temperature(base_temp, hour)
    if weather == "Rain":        temperature -= 2.5
    elif weather == "Heavy Rain": temperature -= 4.5
    temperature = float(np.clip(temperature, 14, 41))
    humidity    = float(np.clip(np.random.normal(70 if season=="Monsoon" else 55, 12), 35, 95))

    # ── TRAFFIC ───────────────────────────────────────────────────
    rh_mult = rush_hour_multiplier(hour, bool(is_weekend), area)
    tw      = area_traffic_weight.get(area, 1.0)
    zone_bump   = {"Central":120,"East":80,"South":60}.get(zone, 0)
    season_bump = 100 if season=="Monsoon" else 0

    base_t  = (500 * rh_mult * tw + zone_bump + season_bump) * growth_factor
    base_t *= random.uniform(0.88, 1.12)
    vehicles = max(30, int(np.random.normal(base_t, 60)))
    vehicles = int(vehicles + 0.12 * neighbor_mean(prev_vehicles, area))

    road            = area_road_type.get(area, "Main Road")
    free_flow_speed = {"Highway":80,"Main Road":55,"Street":35}[road]
    road_capacity   = {"Highway":1200,"Main Road":750,"Street":350}[road]

    v_ratio = vehicles / road_capacity
    speed   = free_flow_speed / (1 + 0.15*(v_ratio**4))
    speed   = float(max(4, speed))

    # holiday / scheduled-event bump
    holiday_mult = holiday_multipliers.get((month, ts.day), 1.0)
    sched_mult   = 1.0
    for (ev_area, s, e, m) in scheduled_events:
        if ev_area == area and date_in_range(ts, s, e):
            sched_mult = max(sched_mult, m)

    if event_active[area] == 0:
        if random.random() < 0.003:
            event_active[area]   = 1
            event_duration[area] = random.randint(4, 10)
    else:
        event_duration[area] -= 1
        if event_duration[area] <= 0:
            event_active[area] = 0
    event = random.choice(events_list) if event_active[area] else "None"

    # weather effects on traffic
    if weather == "Rain":
        speed *= 0.88; vehicles = int(vehicles*0.92)
    elif weather == "Heavy Rain":
        speed *= 0.72; vehicles = int(vehicles*0.78)

    if event != "None":
        if weather == "Rain":        vehicles = int(vehicles*0.85)
        elif weather == "Heavy Rain": vehicles = int(vehicles*0.60)

    # accident probability
    acc_prob = 0.012
    if vehicles > road_capacity*0.9: acc_prob += 0.12
    if speed > 65:                    acc_prob += 0.06
    if weather == "Rain":             acc_prob += 0.06
    elif weather == "Heavy Rain":     acc_prob += 0.14

    if accident_duration[area] > 0:
        incident = "Accident"; severity = "Ongoing"
        accident_duration[area] -= 1
    else:
        if random.random() < acc_prob:
            incident = "Accident"
            severity = random.choice(["Minor","Major","Severe"])
            accident_duration[area] = int(np.random.pareto(1.8)*4) + 1
        else:
            incident = random.choices(["None","Construction","Roadblock"],
                                       weights=[0.88,0.08,0.04])[0]
            severity = "None"

    signal_wait  = int(min(300, vehicles // 5))
    prev_vehicles[area] = float(vehicles)

    v_ratio_final = vehicles / road_capacity
    congestion = ("Low" if v_ratio_final < 0.5
                  else "Medium" if v_ratio_final < 0.85
                  else "High")

    traffic_rec = {
        "timestamp":        ts.strftime("%Y-%m-%dT%H:%M:%S"),
        "area":             area,
        "zone":             zone,
        "vehicle_count":    vehicles,
        "avg_speed":        round(speed, 1),
        "congestion_level": congestion,
        "road_type":        road,
        "weather":          weather,
        "incident":         incident,
        "severity":         severity,
        "event":            event,
        "signal_wait_time": signal_wait,
        "is_weekend":       is_weekend,
        "is_it_hub":        is_it_hub,
        "season":           season,
        "generator_version": GENERATOR_VERSION,
    }

    # ── ENERGY ────────────────────────────────────────────────────
    base_e = 3800
    if season=="Summer":   base_e += 1200
    elif season=="Winter": base_e += 300

    hour_factor = 0.5 + 0.7 * max(0, np.sin((hour-6)*np.pi/14))
    base_e *= hour_factor * area_energy_weight.get(area, 1.0) * growth_factor
    base_e += vehicles * 0.45

    if temperature > 34:   base_e *= 1.18
    elif temperature > 30: base_e *= 1.08
    elif season=="Winter" and temperature < 18: base_e *= 1.06
    if weather=="Rain":        base_e *= 1.03
    elif weather=="Heavy Rain": base_e *= 1.07

    energy = float(max(400, np.random.normal(base_e, 420)))
    energy += 0.10 * neighbor_mean(prev_energy, area)
    energy  = 0.68*prev_energy[area] + 0.32*energy
    prev_energy[area] = energy

    demand = "High" if energy > 6500 else "Medium" if energy > 3000 else "Low"

    outage_prob = 0.003
    if demand=="High" and weather=="Heavy Rain": outage_prob = 0.045
    elif demand=="High":                          outage_prob = 0.012
    elif weather=="Heavy Rain":                   outage_prob = 0.018
    if weather=="Rain":        outage_prob = min(0.2, outage_prob+0.01)
    elif weather=="Heavy Rain": outage_prob = min(0.5, outage_prob+0.03)
    power_outage = 1 if random.random() < outage_prob else 0

    renewable_usage = float(np.clip(solar_renewable(hour)+np.random.normal(0,3), 0, 45))
    load_type = ("Industrial" if area in industrial_areas
                 else "Commercial" if (area in it_areas or zone=="Central")
                 else "Residential")

    # sensor realism: outages / dropout / drift / spike
    if power_outage and outage_counter[area]==0 and random.random()<0.25:
        outage_counter[area] = random.randint(1, 6)

    if outage_counter[area] > 0:
        energy_record = float("nan")
        outage_counter[area] -= 1
    else:
        dp = 0.005 + (0.01 if weather=="Heavy Rain" else 0) + (0.05 if power_outage else 0)
        energy_record = float("nan") if random.random() < dp else round(energy, 1)

    if drift_counter[area] > 0:
        drift_counter[area] -= 1
        energy_record = round(prev_energy[area]*drift_factor[area], 1)
    elif random.random() < 0.0006:
        drift_counter[area] = random.randint(10, 200)
        drift_factor[area]  = random.uniform(1.05, 1.35)
        energy_record = round(prev_energy[area]*drift_factor[area], 1)

    if random.random() < 0.0005:
        base_val = energy_record if not (isinstance(energy_record, float)
                                         and np.isnan(energy_record)) else energy
        energy_record = round(base_val*(1+np.random.pareto(2.0)), 1)

    energy_rec = {
        "timestamp":            ts.strftime("%Y-%m-%dT%H:%M:%S"),
        "area":                 area,
        "zone":                 zone,
        "weather":              weather,
        "energy_consumption":   energy_record,
        "temperature":          round(temperature, 1),
        "humidity":             round(humidity, 1),
        "demand_level":         demand,
        "renewable_usage":      round(renewable_usage, 1),
        "load_type":            load_type,
        "is_weekend":           is_weekend,
        "power_outage":         power_outage,
        "is_it_hub":            is_it_hub,
        "season":               season,
        "generator_version":    GENERATOR_VERSION,
    }

    # ── POLLUTION ─────────────────────────────────────────────────
    base_p = 80 * area_pollution_weight.get(area, 1.0)
    if season=="Winter":   base_p += 50
    elif season=="Monsoon": base_p -= 30
    elif season=="Summer":  base_p += 15
    if zone=="Central": base_p += 25
    elif zone=="East":  base_p += 10
    base_p += vehicles * 0.06

    energy_for_p = (prev_energy[area]
                    if (isinstance(energy_record, float) and np.isnan(energy_record))
                    else float(energy_record))
    base_p += energy_for_p * 0.008

    if weather=="Heavy Rain": base_p -= 50
    elif weather=="Rain":      base_p -= 20
    if season=="Winter" and temperature < 18: base_p += 25

    if incident=="Accident":      base_p += 28
    if congestion=="High":        base_p += 18
    elif congestion=="Medium":    base_p +=  7
    if 8<=hour<=10 or 17<=hour<=20: base_p += 20
    elif 2<=hour<=5:                 base_p -= 15

    base_p *= growth_factor
    if random.random() < 0.0009:
        base_p += np.random.lognormal(mean=4.0, sigma=0.9)

    base_p += 0.18 * neighbor_mean(prev_aqi, area)

    aqi = max(20, int(np.random.normal(base_p, 12)))
    aqi = int(0.68*prev_aqi[area] + 0.32*aqi)
    aqi = int(np.clip(aqi, 20, 350))
    prev_aqi[area] = aqi

    pm25 = float(max(5,  np.random.normal(aqi*0.58, 8)))
    pm10 = float(max(15, np.random.normal(aqi*0.82, 12)))
    no2  = float(max(3,  np.random.normal(aqi*0.28, 5)))
    co   = float(max(0.3,np.random.normal(aqi*0.018, 0.4)))

    pollution_rec = {
        "timestamp":         ts.strftime("%Y-%m-%dT%H:%M:%S"),
        "area":              area,
        "zone":              zone,
        "AQI":               aqi,
        "PM2.5":             round(pm25, 1),
        "PM10":              round(pm10, 1),
        "NO2":               round(no2,  1),
        "CO":                round(co,   2),
        "weather":           weather,
        "temperature":       round(temperature, 1),
        "humidity":          round(humidity, 1),
        "is_weekend":        is_weekend,
        "is_it_hub":         is_it_hub,
        "season":            season,
        "generator_version": GENERATOR_VERSION,
    }

    return {"traffic": traffic_rec, "energy": energy_rec, "pollution": pollution_rec}

# ══════════════════════════════════════════════════════════════════
#  STREAMING API  — called by producer.py
# ══════════════════════════════════════════════════════════════════

# Round-robin area pointer so each batch covers different areas
_area_pointer = 0

def generate_traffic_record(ts: datetime) -> list:
    """
    Return a list of traffic record dicts for the current streaming batch.
    The timestamp `ts` is passed by producer.py but we use our own
    stream-clock for continuity.  The stream-clock advances by
    STREAM_INTERVAL_SECS on every call, regardless of wall-clock time.
    """
    return _generate_stream_batch(ts, "traffic")

def generate_energy_record(ts: datetime) -> list:
    """Return a list of energy record dicts for the current streaming batch."""
    return _generate_stream_batch(ts, "energy")

def generate_pollution_record(ts: datetime) -> list:
    """Return a list of pollution record dicts for the current streaming batch."""
    return _generate_stream_batch(ts, "pollution")

# Internal cache so all three functions for the SAME batch share
# the same records (generated once, split by type).
_batch_cache: dict = {}
_batch_ts = None

def _generate_stream_batch(wall_ts: datetime, record_type: str) -> list:
    """
    Generate (or retrieve from cache) the records for this batch.

    TIMESTAMP CONTINUITY DESIGN
    ───────────────────────────
    • The stream clock starts at STREAM_START (2026-01-01T00:00:00) or
      resumes from stream_state.txt.
    • Every call to generate_traffic_record() (the FIRST of the three per
      batch cycle in producer.py) advances the clock by STREAM_INTERVAL_SECS
      and writes stream_state.txt.
    • generate_energy_record() and generate_pollution_record() read from
      the same _batch_cache, so all three share identical timestamps.
    • On producer restart: _read_stream_state() returns
      last_written_ts + STREAM_INTERVAL_SECS, so we continue exactly
      where we left off with no gap or duplicate.
    """
    global _batch_cache, _batch_ts, _area_pointer

    if record_type == "traffic":
        # Advance stream clock and refresh cache
        stream_ts = _read_stream_state()
        _batch_ts = stream_ts
        _write_stream_state(stream_ts)

        # Select areas for this batch (round-robin, AREAS_PER_BATCH areas)
        batch_areas = []
        for _ in range(AREAS_PER_BATCH):
            batch_areas.append(areas[_area_pointer % len(areas)])
            _area_pointer += 1

        # Generate records for all selected areas at this timestamp
        _batch_cache = {"traffic": [], "energy": [], "pollution": []}
        for area in batch_areas:
            rec = _generate_record(stream_ts, area)
            _batch_cache["traffic"].append(rec["traffic"])
            _batch_cache["energy"].append(rec["energy"])
            _batch_cache["pollution"].append(rec["pollution"])

    # Return the requested type from cache
    return _batch_cache.get(record_type, [])

# ══════════════════════════════════════════════════════════════════
#  HISTORICAL BATCH GENERATOR  — run as main script
#  python Generate_data.py
# ══════════════════════════════════════════════════════════════════
def generate_historical():
    """
    Generate 500 000 sorted historical records spanning 2010–2025.
    Saves traffic.csv, energy.csv, pollution.csv.
    Run ONCE before Stage-1 EDA.
    """
    print(f"Generating {ROWS:,} historical records ({HIST_START.date()} → {HIST_END.date()})...")
    time_diff  = int((HIST_END - HIST_START).total_seconds())
    timestamps = sorted([
        HIST_START + timedelta(seconds=random.randint(0, time_diff))
        for _ in range(ROWS)
    ])

    prev_area = random.choice(areas)
    aw = [area_traffic_weight.get(a, 1.0) for a in areas]
    CONTINUITY = 0.75

    t_rows, e_rows, p_rows = [], [], []

    for i, ts in enumerate(timestamps):
        if random.random() < CONTINUITY:
            area = prev_area
        else:
            area = random.choices(areas, weights=aw, k=1)[0]
        prev_area = area

        rec = _generate_record(ts, area)
        t  = rec["traffic"]
        e  = rec["energy"]
        p  = rec["pollution"]

        t_rows.append([t["timestamp"],t["area"],t["zone"],t["vehicle_count"],
                       t["avg_speed"],t["congestion_level"],t["road_type"],
                       t["weather"],t["incident"],t["severity"],t["event"],
                       t["signal_wait_time"],t["is_weekend"],t["is_it_hub"],
                       t["season"],t["generator_version"]])

        e_rows.append([e["timestamp"],e["area"],e["zone"],e["weather"],
                       e["energy_consumption"],e["temperature"],e["humidity"],
                       e["demand_level"],e["renewable_usage"],e["load_type"],
                       e["is_weekend"],e["power_outage"],e["is_it_hub"],
                       e["season"],e["generator_version"]])

        p_rows.append([p["timestamp"],p["area"],p["zone"],p["AQI"],
                       p["PM2.5"],p["PM10"],p["NO2"],p["CO"],
                       p["weather"],p["temperature"],p["humidity"],
                       p["is_weekend"],p["is_it_hub"],p["season"],
                       p["generator_version"]])

        if (i+1) % 50_000 == 0:
            print(f"  {i+1:>7,} / {ROWS:,} rows generated...")

    pd.DataFrame(t_rows, columns=[
        "timestamp","area","zone","vehicle_count","avg_speed",
        "congestion_level","road_type","weather","incident",
        "severity","event","signal_wait_time","is_weekend","is_it_hub","season",
        "generator_version"
    ]).to_csv("traffic.csv", index=False)

    pd.DataFrame(e_rows, columns=[
        "timestamp","area","zone","weather","energy_consumption",
        "temperature","humidity","demand_level","renewable_usage","load_type",
        "is_weekend","power_outage","is_it_hub","season",
        "generator_version"
    ]).to_csv("energy.csv", index=False)

    pd.DataFrame(p_rows, columns=[
        "timestamp","area","zone","AQI","PM2.5","PM10","NO2","CO",
        "weather","temperature","humidity","is_weekend","is_it_hub","season",
        "generator_version"
    ]).to_csv("pollution.csv", index=False)

    print("\n✅ Historical data generated:")
    print(f"   Window  : {HIST_START.date()} → {HIST_END.date()}")
    print(f"   Version : {GENERATOR_VERSION}")
    print(f"   Traffic  rows : {len(t_rows):,}")
    print(f"   Energy   rows : {len(e_rows):,}")
    print(f"   Pollution rows: {len(p_rows):,}")

if __name__ == "__main__":
    generate_historical()