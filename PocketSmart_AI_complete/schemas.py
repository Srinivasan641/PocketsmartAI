from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def username_clean(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError("Username may contain letters, numbers and underscores only.")
        return v.strip()

    @field_validator("confirm_password")
    @classmethod
    def password_placeholder(cls, v):
        return v

class LoginInput(BaseModel):
    username: str
    password: str

class HomeInput(BaseModel):
    total_budget: float = Field(gt=0)
    room_details: str = Field(min_length=2, max_length=500)
    lighting_requirements: int = Field(default=0, ge=0, le=100)
    ceiling_fan_requirements: int = Field(default=0, ge=0, le=100)
    furniture_requirements: str = Field(default="", max_length=500)
    table_quantity: int = Field(default=0, ge=0, le=100)
    preferences: str = Field(default="", max_length=500)
    additional_requirements: str = Field(default="", max_length=1000)

class PartyInput(BaseModel):
    total_budget: float = Field(gt=0)
    guests: int = Field(gt=0, le=10000)
    event_type: str = Field(min_length=2, max_length=100)
    venue_type: str = Field(min_length=2, max_length=100)
    catering: bool = True
    decoration: bool = True
    entertainment: bool = True
    additional_requirements: str = Field(default="", max_length=1000)

class JewelryInput(BaseModel):
    budget: float = Field(gt=0)
    occasion: str = Field(min_length=2, max_length=100)
    style_preference: str = Field(default="", max_length=500)
    outfit_description: str = Field(default="", max_length=1000)

class Item(BaseModel):
    name: str
    description: str
    estimated_price: float = Field(ge=0)
    quantity: int = Field(ge=1)
    category: str
    platform: str
    shopping_link: str
    demo_data: bool = True

class Allocation(BaseModel):
    category: str
    allocated_budget: float = Field(ge=0)
    items: List[Item] = []

class RecommendationResult(BaseModel):
    planner_type: Literal["home", "party", "jewelry"]
    total_budget: float = Field(ge=0)
    allocations: List[Allocation]
    remaining_budget: float = Field(ge=0)
    additional_suggestions: List[str] = []
    data_notice: str = "Demo/search-link data unless an official integration is configured."
