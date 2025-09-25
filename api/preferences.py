from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

from database import (
    DEFAULT_USER_REF,
    StrategyPreference,
    get_db,
    get_or_create_preference,
)

router = APIRouter(prefix="/preferences", tags=["preferences"])

PRODUCT_OPTIONS = [
    "BTC",
    "ETH",
    "XRP",
    "SOL",
    "BNB",
    "DOGE",
    "NIFTY",
    "BANKNIFTY",
    "NASDAQ",
    "S&P",
    "DJ 30",
    "OPTIONS",
]

STRATEGY_OPTIONS = [
    "ALSAPRO 1",
    "ALSAPRO 2",
    "ALSAPRO 3",
    "ALSAPRO 4",
    "ALSAPRO 5",
]

DIRECTION_OPTIONS = [
    "allow_long_short",
    "allow_long_only",
    "allow_short_only",
]

LEVERAGE_OPTIONS = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
CAPITAL_MIN = 1
CAPITAL_MAX = 100


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: Optional[str] = None
    strategy: Optional[str] = None
    direction_mode: Optional[str] = None
    leverage: Optional[float] = None
    capital_allocation_percent: Optional[float] = None


class ProductSelection(BaseModel):
    product: str

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        if value not in PRODUCT_OPTIONS:
            raise ValueError("Unsupported product")
        return value


class StrategySelection(BaseModel):
    strategy: str

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, value: str) -> str:
        if value not in STRATEGY_OPTIONS:
            raise ValueError("Unsupported strategy")
        return value


class DirectionSelection(BaseModel):
    direction_mode: str

    @field_validator("direction_mode")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in DIRECTION_OPTIONS:
            raise ValueError("Unsupported direction mode")
        return value


class LeverageSelection(BaseModel):
    leverage: float

    @field_validator("leverage")
    @classmethod
    def validate_leverage(cls, value: float) -> float:
        if value not in LEVERAGE_OPTIONS:
            raise ValueError("Unsupported leverage value")
        return value


class CapitalSelection(BaseModel):
    capital_allocation_percent: float

    @field_validator("capital_allocation_percent")
    @classmethod
    def validate_allocation(cls, value: float) -> float:
        if value < CAPITAL_MIN or value > CAPITAL_MAX:
            raise ValueError("Capital allocation must be between 1 and 100")
        return value




def _update_preference(
    db: Session,
    update_data: Dict[str, object],
    user_ref: str = DEFAULT_USER_REF,
) -> StrategyPreference:
    preference = get_or_create_preference(db, user_ref=user_ref)
    for key, value in update_data.items():
        setattr(preference, key, value)
    db.commit()
    db.refresh(preference)
    return preference


@router.get("/options")
def list_options() -> Dict[str, object]:
    return {
        "products": PRODUCT_OPTIONS,
        "strategies": STRATEGY_OPTIONS,
        "directions": DIRECTION_OPTIONS,
        "leverages": LEVERAGE_OPTIONS,
        "capital_range": {"min": CAPITAL_MIN, "max": CAPITAL_MAX},
    }


@router.get("/current", response_model=PreferenceResponse)
def get_current_preferences(
    db: Session = Depends(get_db),
    user_ref: str = DEFAULT_USER_REF,
) -> StrategyPreference:
    preference = get_or_create_preference(db, user_ref=user_ref)
    return preference


@router.post("/product", response_model=PreferenceResponse)
def set_product(
    selection: ProductSelection,
    db: Session = Depends(get_db),
    user_ref: str = DEFAULT_USER_REF,
) -> StrategyPreference:
    return _update_preference(db, {"product": selection.product}, user_ref=user_ref)


@router.post("/strategy", response_model=PreferenceResponse)
def set_strategy(
    selection: StrategySelection,
    db: Session = Depends(get_db),
    user_ref: str = DEFAULT_USER_REF,
) -> StrategyPreference:
    return _update_preference(db, {"strategy": selection.strategy}, user_ref=user_ref)


@router.post("/direction", response_model=PreferenceResponse)
def set_direction(
    selection: DirectionSelection,
    db: Session = Depends(get_db),
    user_ref: str = DEFAULT_USER_REF,
) -> StrategyPreference:
    return _update_preference(db, {"direction_mode": selection.direction_mode}, user_ref=user_ref)


@router.post("/leverage", response_model=PreferenceResponse)
def set_leverage(
    selection: LeverageSelection,
    db: Session = Depends(get_db),
    user_ref: str = DEFAULT_USER_REF,
) -> StrategyPreference:
    return _update_preference(db, {"leverage": selection.leverage}, user_ref=user_ref)


@router.post("/capital", response_model=PreferenceResponse)
def set_capital(
    selection: CapitalSelection,
    db: Session = Depends(get_db),
    user_ref: str = DEFAULT_USER_REF,
) -> StrategyPreference:
    return _update_preference(
        db,
        {"capital_allocation_percent": selection.capital_allocation_percent},
        user_ref=user_ref,
    )


