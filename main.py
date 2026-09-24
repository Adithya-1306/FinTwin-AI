from __future__ import annotations
from market_data import get_single_stock
import json
import math
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "fintwin.db"
STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FinTwin AI",
    version="1.0.0",
    description="Hackathon MVP: personalized financial twin + what-if simulator + explainable decision engine",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class Profile(BaseModel):
    name: str = "Aarav"
    age: int = Field(28, ge=18, le=100)
    monthly_income: float = Field(80000, ge=0)
    monthly_expenses: float = Field(42000, ge=0)
    liquid_savings: float = Field(180000, ge=0)
    debt_emi: float = Field(5000, ge=0)
    dependents: int = Field(1, ge=0, le=20)
    risk_tolerance: Literal["low", "moderate", "high"] = "moderate"
    investment_horizon_years: int = Field(10, ge=1, le=50)


class GoalIn(BaseModel):
    title: str
    target_amount: float = Field(..., gt=0)
    years: float = Field(..., gt=0, le=50)
    priority: Literal["high", "medium", "low"] = "medium"


class HoldingIn(BaseModel):
    symbol: str
    name: str
    quantity: float = Field(..., gt=0)
    avg_price: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    sector: str


class SimulationIn(BaseModel):
    monthly_investment: float = Field(5000, ge=0)
    years: int = Field(5, ge=1, le=40)
    crash_percent: float = Field(25, ge=0, le=80)
    job_loss_months: int = Field(0, ge=0, le=24)


class RecommendationIn(BaseModel):
    symbol: str
    
    
class RiskAssessmentIn(BaseModel):
    market_drop_response: Literal["sell", "hold", "buy_more"]
    income_stability: Literal["stable", "moderate", "variable"]
    investment_horizon: Literal["short", "medium", "long"]
    portfolio_drop_response: Literal["reduce", "continue", "increase"]
    wealth_priority: Literal["preserve", "balanced", "growth"]


MARKET = {
    "RELIANCE": {
        "name": "Reliance Industries",
        "sector": "Energy / Consumer",
        "pe_quality": 0.68,
        "earnings": 0.74,
        "technical": 0.61,
        "news": 0.70,
        "volatility": 0.64,
        "trend": "Positive",
    },
    "TCS": {
        "name": "Tata Consultancy Services",
        "sector": "IT Services",
        "pe_quality": 0.72,
        "earnings": 0.78,
        "technical": 0.66,
        "news": 0.64,
        "volatility": 0.42,
        "trend": "Positive",
    },
    "HDFCBANK": {
        "name": "HDFC Bank",
        "sector": "Banking",
        "pe_quality": 0.76,
        "earnings": 0.80,
        "technical": 0.58,
        "news": 0.69,
        "volatility": 0.38,
        "trend": "Neutral",
    },
    "INFY": {
        "name": "Infosys",
        "sector": "IT Services",
        "pe_quality": 0.66,
        "earnings": 0.70,
        "technical": 0.54,
        "news": 0.57,
        "volatility": 0.48,
        "trend": "Neutral",
    },
    "ICICIBANK": {
        "name": "ICICI Bank",
        "sector": "Banking",
        "pe_quality": 0.79,
        "earnings": 0.82,
        "technical": 0.72,
        "news": 0.73,
        "volatility": 0.41,
        "trend": "Positive",
    },
}


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                target_amount REAL NOT NULL,
                years REAL NOT NULL,
                priority TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_price REAL NOT NULL,
                current_price REAL NOT NULL,
                sector TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                symbol TEXT NOT NULL,
                from_action TEXT,
                to_action TEXT NOT NULL,
                reason TEXT NOT NULL
            );
            """
        )
        if not conn.execute("SELECT 1 FROM profile WHERE id=1").fetchone():
            conn.execute("INSERT INTO profile (id, data) VALUES (1, ?)", (Profile().model_dump_json(),))
        if conn.execute("SELECT COUNT(*) c FROM goals").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO goals (title, target_amount, years, priority) VALUES (?,?,?,?)",
                [
                    ("Emergency Fund", 300000, 1.5, "high"),
                    ("Car", 1200000, 5, "medium"),
                    ("House Down Payment", 4000000, 10, "high"),
                ],
            )
        if conn.execute("SELECT COUNT(*) c FROM holdings").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO holdings (symbol,name,quantity,avg_price,current_price,sector) VALUES (?,?,?,?,?,?)",
                [
                    ("RELIANCE", "Reliance Industries", 18, 2520, 2865, "Energy / Consumer"),
                    ("TCS", "Tata Consultancy Services", 9, 3410, 3875, "IT Services"),
                    ("HDFCBANK", "HDFC Bank", 24, 1510, 1688, "Banking"),
                ],
            )
        if conn.execute("SELECT COUNT(*) c FROM timeline").fetchone()["c"] == 0:
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT INTO timeline (ts,symbol,from_action,to_action,reason) VALUES (?,?,?,?,?)",
                [
                    (now, "TCS", "INCREASE", "HOLD", "Valuation expanded while the user's IT-sector allocation moved above the preferred band."),
                    (now, "HDFCBANK", "HOLD", "INCREASE", "Earnings quality improved and banking exposure remained within the user's diversification limit."),
                ],
            )


def get_profile() -> Profile:
    with db() as conn:
        row = conn.execute("SELECT data FROM profile WHERE id=1").fetchone()
    return Profile(**json.loads(row["data"]))


def get_holdings():
    with db() as conn:
        rows = conn.execute("SELECT * FROM holdings ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_goals():
    with db() as conn:
        rows = conn.execute("SELECT * FROM goals ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, years").fetchall()
    return [dict(r) for r in rows]


def clamp(v: float, lo=0, hi=100):
    return max(lo, min(hi, v))


def health_score(profile: Profile, holdings: list[dict], goals: list[dict]):
    surplus = max(0, profile.monthly_income - profile.monthly_expenses - profile.debt_emi)
    emergency_months = profile.liquid_savings / max(profile.monthly_expenses + profile.debt_emi, 1)
    emergency = clamp((emergency_months / 6) * 100)

    debt_ratio = profile.debt_emi / max(profile.monthly_income, 1)
    debt = clamp(100 - debt_ratio * 260)

    savings_rate = surplus / max(profile.monthly_income, 1)
    discipline = clamp(savings_rate / 0.30 * 100)

    total = sum(h["quantity"] * h["current_price"] for h in holdings)
    sector_values = {}
    for h in holdings:
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0) + h["quantity"] * h["current_price"]
    max_sector = max(sector_values.values(), default=0) / max(total, 1)
    diversification = clamp(100 - max(0, max_sector - 0.35) * 140)

    risk_target = {"low": 0.35, "moderate": 0.60, "high": 0.80}[profile.risk_tolerance]
    equity_proxy = min(0.95, 0.35 + len(holdings) * 0.1)
    risk_exposure = clamp(100 - abs(equity_proxy - risk_target) * 130)

    goal_pressure = 0
    if goals:
        near = [g for g in goals if g["years"] <= 3]
        goal_pressure = len(near) * 5
    goal_readiness = clamp(72 + savings_rate * 50 - goal_pressure)

    components = {
        "Emergency fund": round(emergency),
        "Risk exposure": round(risk_exposure),
        "Diversification": round(diversification),
        "Debt burden": round(debt),
        "Investment discipline": round(discipline),
        "Goal readiness": round(goal_readiness),
    }
    overall = round(
        emergency * 0.22
        + risk_exposure * 0.15
        + diversification * 0.15
        + debt * 0.18
        + discipline * 0.18
        + goal_readiness * 0.12
    )
    messages = []
    if emergency_months < 3:
        messages.append(f"Emergency reserves cover only {emergency_months:.1f} months of current outgo; improve this before increasing portfolio risk.")
    elif emergency_months < 6:
        messages.append(f"Emergency reserves cover {emergency_months:.1f} months; target roughly 6 months for a stronger buffer.")
    else:
        messages.append(f"Emergency reserves cover {emergency_months:.1f} months, providing a solid liquidity buffer.")
    if savings_rate < 0.15:
        messages.append("Monthly investable surplus is relatively tight, so aggressive goal assumptions should be avoided.")
    else:
        messages.append(f"Current investable surplus is about ₹{surplus:,.0f}/month ({savings_rate*100:.0f}% of income).")
    return {
        "overall": overall,
        "components": components,
        "emergency_months": round(emergency_months, 1),
        "monthly_surplus": round(surplus),
        "savings_rate": round(savings_rate * 100, 1),
        "messages": messages,
    }

def dynamic_risk_profile(profile: Profile, answers: RiskAssessmentIn):
    """
    Calculates a user's risk profile from:
    1. Financial capacity
    2. Behavioural risk tolerance
    3. Investment need
    """

    # ---------------------------------------------------------
    # 1. RISK CAPACITY
    # How much financial risk can the person actually afford?
    # ---------------------------------------------------------

    monthly_outgo = profile.monthly_expenses + profile.debt_emi
    emergency_months = profile.liquid_savings / max(monthly_outgo, 1)

    # Emergency savings
    if emergency_months >= 9:
        emergency_score = 100
    elif emergency_months >= 6:
        emergency_score = 85
    elif emergency_months >= 3:
        emergency_score = 60
    else:
        emergency_score = 30

    # Debt burden
    debt_ratio = profile.debt_emi / max(profile.monthly_income, 1)

    if debt_ratio <= 0.10:
        debt_score = 90
    elif debt_ratio <= 0.20:
        debt_score = 70
    elif debt_ratio <= 0.35:
        debt_score = 50
    else:
        debt_score = 25

    # Dependents reduce risk capacity
    dependent_score = max(30, 100 - profile.dependents * 10)

    # Longer investment horizon increases capacity
    if profile.investment_horizon_years >= 10:
        horizon_score = 90
    elif profile.investment_horizon_years >= 5:
        horizon_score = 70
    else:
        horizon_score = 45

    risk_capacity = round(
        emergency_score * 0.35
        + debt_score * 0.25
        + dependent_score * 0.15
        + horizon_score * 0.25
    )

    # ---------------------------------------------------------
    # 2. RISK TOLERANCE
    # How comfortable is the person with market risk?
    # ---------------------------------------------------------

    crash_scores = {
        "sell": 25,
        "hold": 65,
        "buy_more": 95,
    }

    portfolio_scores = {
        "reduce": 25,
        "continue": 65,
        "increase": 95,
    }

    income_scores = {
        "stable": 90,
        "moderate": 65,
        "variable": 35,
    }

    wealth_scores = {
        "preserve": 30,
        "balanced": 65,
        "growth": 95,
    }

    risk_tolerance = round(
        crash_scores[answers.market_drop_response] * 0.35
        + portfolio_scores[answers.portfolio_drop_response] * 0.25
        + income_scores[answers.income_stability] * 0.15
        + wealth_scores[answers.wealth_priority] * 0.25
    )

    # ---------------------------------------------------------
    # 3. RISK NEED
    # How much risk might be required to reach the person's goals?
    # ---------------------------------------------------------

    if answers.investment_horizon == "long":
        risk_need = 80
    elif answers.investment_horizon == "medium":
        risk_need = 60
    else:
        risk_need = 35

    # ---------------------------------------------------------
    # 4. FINAL PROFILE
    # ---------------------------------------------------------

    overall = round(
        risk_capacity * 0.40
        + risk_tolerance * 0.40
        + risk_need * 0.20
    )

    if overall < 45:
        profile_name = "CONSERVATIVE"
    elif overall < 70:
        profile_name = "MODERATE"
    else:
        profile_name = "AGGRESSIVE"

    return {
        "risk_profile": profile_name,
        "overall_score": overall,
        "risk_capacity": risk_capacity,
        "risk_tolerance": risk_tolerance,
        "risk_need": risk_need,
        "emergency_months": round(emergency_months, 1),
    }



def expected_return(profile: Profile):
    base = {"low": 0.07, "moderate": 0.10, "high": 0.125}[profile.risk_tolerance]
    if profile.investment_horizon_years < 3:
        base -= 0.015
    return max(0.04, base)


def simulate(profile: Profile, request: SimulationIn):
    annual = expected_return(profile)
    monthly_r = (1 + annual) ** (1 / 12) - 1
    total_months = request.years * 12
    baseline = profile.liquid_savings
    stressed = profile.liquid_savings * (1 - request.crash_percent / 100)
    baseline_points = [{"month": 0, "value": round(baseline)}]
    stressed_points = [{"month": 0, "value": round(stressed)}]
    draw = max(0, profile.monthly_expenses + profile.debt_emi - profile.monthly_income * 0.15)

    for m in range(1, total_months + 1):
        baseline = baseline * (1 + monthly_r) + request.monthly_investment

        in_job_loss = m <= request.job_loss_months
        stressed_contribution = 0 if in_job_loss else request.monthly_investment
        stressed = stressed * (1 + monthly_r) + stressed_contribution
        if in_job_loss:
            stressed -= draw
        stressed = max(stressed, 0)

        if m % 12 == 0 or m == total_months:
            baseline_points.append({"month": m, "value": round(baseline)})
            stressed_points.append({"month": m, "value": round(stressed)})

    return {
        "assumed_annual_return": round(annual * 100, 1),
        "baseline_final": round(baseline),
        "stressed_final": round(stressed),
        "difference": round(baseline - stressed),
        "baseline_points": baseline_points,
        "stressed_points": stressed_points,
        "summary": f"Under the stress case, projected wealth is ₹{baseline-stressed:,.0f} lower after {request.years} years. This combines a {request.crash_percent:.0f}% starting shock with {request.job_loss_months} months of paused investing and expense pressure.",
    }


def recommendation(profile: Profile, holdings: list[dict], symbol: str):
    symbol = symbol.upper().strip()

    # Get live market data
    live = get_single_stock(symbol)

    if not live:
        raise HTTPException(
            404,
            f"Could not find market data for {symbol}."
        )

    # Use existing demo fundamentals when available.
    # For new stocks, use neutral starting values.
    base = MARKET.get(symbol, {
        "name": symbol,
        "sector": "NSE Equity",
        "pe_quality": 0.50,
        "earnings": 0.50,
        "technical": 0.50,
        "news": 0.50,
        "volatility": 0.50,
        "trend": "Neutral",
    })

    m = {
        **base,
        "live_price": live.get("price"),
        "previous_close": live.get("previous_close"),
        "change_percent": live.get("change_percent"),
        "day_high": live.get("day_high"),
        "day_low": live.get("day_low"),
        "year_high": live.get("year_high"),
        "year_low": live.get("year_low"),
        "market_state": live.get("market_state"),
    }

    # Portfolio exposure
    total = sum(
        h["quantity"] * h["current_price"]
        for h in holdings
    )

    holding = next(
        (h for h in holdings if h["symbol"] == symbol),
        None
    )

    symbol_value = (
        holding["quantity"] * holding["current_price"]
        if holding else 0
    )

    exposure = symbol_value / max(total, 1)

    # Risk adjustment
    risk_penalty = (
        m["volatility"]
        * {
            "low": 0.30,
            "moderate": 0.16,
            "high": 0.07
        }[profile.risk_tolerance]
    )

    # Concentration adjustment
    concentration_penalty = max(
        0,
        exposure - 0.25
    ) * 0.8

    # FinTwin decision score
    score = (
        m["pe_quality"] * 0.22
        + m["earnings"] * 0.27
        + m["technical"] * 0.19
        + m["news"] * 0.14
        + (1 - m["volatility"]) * 0.18
        - risk_penalty
        - concentration_penalty
    )

    score = max(0, min(1, score))

    # Decision
    if score >= 0.62 and exposure < 0.28:
        action = "INCREASE"
        color = "green"

    elif score < 0.46 or exposure >= 0.35:
        action = "REDUCE"
        color = "red"

    else:
        action = "HOLD"
        color = "amber"

    # Confidence
    confidence = round(
        58 + abs(score - 0.54) * 135
    )
    confidence = min(confidence, 93)

    # Explanation
    reasons = [
        f"Earnings-quality signal: {round(m['earnings'] * 100)} / 100.",
        f"Valuation-quality signal: {round(m['pe_quality'] * 100)} / 100.",
        f"Technical momentum: {round(m['technical'] * 100)} / 100 with a {m['trend'].lower()} trend.",
        f"News-sentiment proxy: {round(m['news'] * 100)} / 100.",
    ]

    if exposure > 0:
        reasons.append(
            f"Current position is about {exposure * 100:.1f}% of the tracked equity portfolio."
        )
    else:
        reasons.append(
            "The stock is not currently held, so there is no single-stock concentration yet."
        )

    return {
        "symbol": symbol,
        "company": m["name"],
        "action": action,
        "confidence": confidence,
        "score": round(score * 100),
        "color": color,
        "sector": m["sector"],
        "portfolio_exposure": round(exposure * 100, 1),
        "reasons": reasons,

        # Live market information
        "live_price": m.get("live_price"),
        "previous_close": m.get("previous_close"),
        "change_percent": m.get("change_percent"),
        "day_high": m.get("day_high"),
        "day_low": m.get("day_low"),
        "year_high": m.get("year_high"),
        "year_low": m.get("year_low"),
        "market_state": m.get("market_state"),

        "data_source": "Live market data",

        "explanation": (
            f"{action} is the current FinTwin decision because "
            f"the combined score is {score * 100:.0f}/100 "
            f"after adjusting for the user's "
            f"{profile.risk_tolerance} risk tolerance "
            f"and portfolio concentration."
        ),
    }

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/dashboard")
def dashboard():
    profile = get_profile()
    holdings = get_holdings()
    goals = get_goals()
    return {
        "profile": profile.model_dump(),
        "holdings": holdings,
        "goals": goals,
        "health": health_score(profile, holdings, goals),
        "market_symbols": list(MARKET.keys()),
    }


@app.get("/api/profile")
def profile_get():
    return get_profile()


@app.post("/api/profile")
def profile_save(profile: Profile):
    with db() as conn:
        conn.execute("UPDATE profile SET data=? WHERE id=1", (profile.model_dump_json(),))
    return {"ok": True, "profile": profile}


@app.get("/api/goals")
def goals_get():
    return get_goals()


@app.post("/api/goals")
def goals_add(goal: GoalIn):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO goals (title,target_amount,years,priority) VALUES (?,?,?,?)",
            (goal.title, goal.target_amount, goal.years, goal.priority),
        )
        goal_id = cur.lastrowid
    return {"id": goal_id, **goal.model_dump()}


@app.delete("/api/goals/{goal_id}")
def goals_delete(goal_id: int):
    with db() as conn:
        cur = conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Goal not found")
    return {"ok": True}


@app.get("/api/portfolio")
def portfolio_get():
    return get_holdings()


@app.post("/api/portfolio")
def portfolio_add(holding: HoldingIn):
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO holdings (symbol,name,quantity,avg_price,current_price,sector) VALUES (?,?,?,?,?,?)",
                (
                    holding.symbol.upper(),
                    holding.name,
                    holding.quantity,
                    holding.avg_price,
                    holding.current_price,
                    holding.sector,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "That symbol is already in the demo portfolio")
    return {"id": cur.lastrowid, **holding.model_dump(), "symbol": holding.symbol.upper()}


@app.delete("/api/portfolio/{holding_id}")
def portfolio_delete(holding_id: int):
    with db() as conn:
        cur = conn.execute("DELETE FROM holdings WHERE id=?", (holding_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Holding not found")
    return {"ok": True}


@app.post("/api/simulate")
def simulate_api(request: SimulationIn):
    return simulate(get_profile(), request)


@app.post("/api/recommendation")
def recommendation_api(request: RecommendationIn):
    return recommendation(get_profile(), get_holdings(), request.symbol)

@app.post("/api/risk-assessment")
def risk_assessment_api(request: RiskAssessmentIn):
    profile = get_profile()
    return dynamic_risk_profile(profile, request)


@app.get("/api/timeline")
def timeline_get():
    with db() as conn:
        rows = conn.execute("SELECT * FROM timeline ORDER BY id DESC LIMIT 20").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/health")
def health_get():
    p = get_profile()
    h = get_holdings()
    g = get_goals()
    return health_score(p, h, g)
