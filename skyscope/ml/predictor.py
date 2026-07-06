import os
import pickle

import joblib
import pandas as pd
from catboost import CatBoostClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")

MONTH_TO_SEASON = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall", 10: "Fall", 11: "Fall",
}

DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


def _time_to_minutes(hour: int, minute: int = 0) -> int:
    return hour * 60 + minute


def _catboost_time_bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Night"


def _rf_time_bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Red-Eye"


def _elapsed_minutes(dep_minutes: int, arr_minutes: int) -> int:
    if arr_minutes >= dep_minutes:
        return arr_minutes - dep_minutes
    return (1440 - dep_minutes) + arr_minutes


def _lookup(mapping, key, default):
    return mapping.get(key, default)


class FlightDelayPredictor:
    _instance = None

    def __init__(self):
        self.catboost = CatBoostClassifier()
        self.catboost.load_model(os.path.join(MODELS_DIR, "flight_delay_classifier.cbm"))

        self.rf_reg = joblib.load(os.path.join(MODELS_DIR, "rf_reg.pkl"))

        with open(os.path.join(MODELS_DIR, "encoders_clf.pkl"), "rb") as f:
            self.encoders_clf = pickle.load(f)

        with open(os.path.join(MODELS_DIR, "encoders_reg.pkl"), "rb") as f:
            self.encoders_reg = pickle.load(f)

        with open(os.path.join(MODELS_DIR, "columns_reg.pkl"), "rb") as f:
            self.columns_reg = pickle.load(f)

        with open(os.path.join(MODELS_DIR, "dropdown_options.pkl"), "rb") as f:
            self.dropdown = pickle.load(f)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_form_options(self):
        return {
            "airlines": self.dropdown["Airline"],
            "airports": self.dropdown["Origin"],
            "days_of_week": DAYS_OF_WEEK,
        }

    def _build_catboost_features(
        self,
        airline,
        origin,
        dest,
        dep_minutes,
        arr_minutes,
        distance,
        month,
        day_of_week,
        is_weekend,
    ):
        season = MONTH_TO_SEASON[month]
        dep_hour = dep_minutes // 60
        dep_time_of_day = _catboost_time_bucket(dep_hour)

        return pd.DataFrame([{
            "Airline": airline,
            "Origin": origin,
            "Dest": dest,
            "CRSDepTime": dep_minutes,
            "CRSArrTime": arr_minutes,
            "Distance": distance,
            "Flight_Month": month,
            "Flight_DayOfWeek": day_of_week,
            "Is_Weekend": is_weekend,
            "Season": season,
            "DepTimeOfDay": dep_time_of_day,
        }])

    def _build_rf_features(
        self,
        airline,
        origin,
        dest,
        dep_minutes,
        arr_minutes,
        distance,
        month,
        day_of_week,
        is_weekend,
    ):
        season = MONTH_TO_SEASON[month]
        dep_hour = dep_minutes // 60
        time_bucket = _rf_time_bucket(dep_hour)
        elapsed = _elapsed_minutes(dep_minutes, arr_minutes)

        global_clf = self.encoders_clf["global_mean_clf"]
        global_reg = self.encoders_reg["global_mean_reg"]

        row = {
            "Flight_Month": month,
            "Flight_DayOfWeek": day_of_week,
            "Is_Weekend": is_weekend,
            "CRSDepTime": dep_minutes,
            "CRSArrTime": arr_minutes,
            "CRSElapsedTime": elapsed,
            "Origin": _lookup(self.encoders_reg["Origin"], origin, global_reg),
            "Dest": _lookup(self.encoders_reg["Dest"], dest, global_reg),
            "Airline": _lookup(self.encoders_reg["Airline"], airline, global_reg),
            "Distance": distance,
            "Route_DelayRate": _lookup(
                self.encoders_clf["Route_DelayRate"], f"{origin}_{dest}", global_clf
            ),
            "Origin_Month_DelayRate": _lookup(
                self.encoders_clf["Origin_Month_DelayRate"], (origin, month), global_clf
            ),
            "Airline_DepTimeOfDay_DelayRate": _lookup(
                self.encoders_clf["Airline_DepTimeOfDay_DelayRate"],
                (airline, time_bucket),
                global_clf,
            ),
            "Origin_Traffic": _lookup(
                self.encoders_clf["Origin_Traffic"], origin, global_clf
            ),
            "DepTimeOfDay_Evening": 1 if time_bucket == "Evening" else 0,
            "DepTimeOfDay_Morning": 1 if time_bucket == "Morning" else 0,
            "DepTimeOfDay_Red-Eye": 1 if time_bucket == "Red-Eye" else 0,
            "Season_Summer": 1 if season == "Summer" else 0,
            "Season_Winter": 1 if season == "Winter" else 0,
        }
        return pd.DataFrame([row])[self.columns_reg]

    def predict(self, payload: dict) -> dict:
        airline = payload["airline"]
        origin = payload["origin"].upper()
        dest = payload["destination"].upper()

        if origin == dest:
            raise ValueError("Origin and destination must be different.")

        dep_minutes = _time_to_minutes(
            int(payload["departure_hour"]),
            int(payload.get("departure_minute", 0)),
        )
        arr_minutes = _time_to_minutes(
            int(payload["arrival_hour"]),
            int(payload.get("arrival_minute", 0)),
        )
        distance = int(payload["distance"])
        month = int(payload["month"])
        day_of_week = int(payload["day_of_week"])
        is_weekend = 1 if payload.get("day_of_week_name") in ("Saturday", "Sunday") else 0

        cat_features = self._build_catboost_features(
            airline, origin, dest, dep_minutes, arr_minutes,
            distance, month, day_of_week, is_weekend,
        )
        proba = self.catboost.predict_proba(cat_features)[0]
        delay_probability = float(proba[1])
        is_delayed = delay_probability >= 0.5

        rf_features = self._build_rf_features(
            airline, origin, dest, dep_minutes, arr_minutes,
            distance, month, day_of_week, is_weekend,
        )
        estimated_delay = float(self.rf_reg.predict(rf_features)[0])
        estimated_delay = max(0.0, round(estimated_delay, 1))

        return {
            "prediction": "Delayed" if is_delayed else "On Time",
            "probability": round(delay_probability * 100, 1),
            "delayed": is_delayed,
            "estimated_delay_minutes": estimated_delay,
        }
