import json
import re
from typing import Optional
from schemas import HomeInput, PartyInput, JewelryInput, RecommendationResult
from config import settings

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

PLATFORM_SEARCH = {
    "Amazon": "https://www.amazon.in/s?k={q}",
    "Flipkart": "https://www.flipkart.com/search?q={q}",
    "IKEA": "https://www.ikea.com/in/en/search/?q={q}",
    "Swiggy": "https://www.swiggy.com/search?query={q}",
    "Zomato": "https://www.zomato.com/search?q={q}",
    "OYO": "https://www.oyorooms.com/search?location={q}",
}

def search_link(platform, query):
    from urllib.parse import quote_plus
    return PLATFORM_SEARCH.get(platform, "https://www.google.com/search?q={q}").format(q=quote_plus(query))

def _client():
    if not settings.gemini_api_key or genai is None:
        return None
    try:
        return genai.Client(api_key=settings.gemini_api_key)
    except Exception:
        return None

def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)

def _prompt(planner_type, payload):
    return f"""You are PocketSmart AI, a budget-aware recommendation assistant.\nPlanner: {planner_type}\nInput JSON: {json.dumps(payload, ensure_ascii=False)}\n\nReturn ONLY valid JSON with this exact top-level shape:\n{{\"planner_type\": \"{planner_type}\", \"total_budget\": number, \"allocations\": [{{\"category\": string, \"allocated_budget\": number, \"items\": [{{\"name\": string, \"description\": string, \"estimated_price\": number, \"quantity\": integer, \"category\": string, \"platform\": string, \"shopping_link\": string, \"demo_data\": true}}]}}], \"remaining_budget\": number, \"additional_suggestions\": [string], \"data_notice\": string}}\nKeep total estimated item cost at or below total_budget. Use safe search links rather than claiming live inventory. Mark data as demo_data=true unless a live official API is actually available.\n"""

def _generate_with_gemini(planner_type, payload, image_bytes=None, mime_type=None):
    client = _client()
    if not client:
        return None
    prompt = _prompt(planner_type, payload)
    contents = [prompt]
    if image_bytes and types:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/jpeg"))
        contents[0] += "\nAnalyze the attached outfit image for broad colors/style only; do not identify the person."
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json") if types else None,
        )
        return _extract_json(response.text)
    except Exception:
        return None

def _item(name, desc, price, qty, category, platform):
    return {"name": name, "description": desc, "estimated_price": round(float(price),2), "quantity": int(qty), "category": category, "platform": platform, "shopping_link": search_link(platform, name), "demo_data": True}

def _normalize(raw, planner_type, budget):
    result = RecommendationResult.model_validate(raw)
    if result.planner_type != planner_type:
        result.planner_type = planner_type
    result.total_budget = budget
    running = 0.0
    allocations = []
    for alloc in result.allocations:
        items=[]
        alloc_total=0.0
        for item in alloc.items:
            allowed = max(0, budget-running)
            if allowed <= 0: break
            unit = min(item.estimated_price, allowed/max(item.quantity,1))
            qty = min(item.quantity, max(1, int(allowed//max(unit,0.01))))
            if unit*qty > allowed: qty = max(1, int(allowed//max(unit,0.01)))
            if unit*qty > allowed: continue
            item.estimated_price = round(unit,2)
            item.quantity = qty
            items.append(item)
            alloc_total += unit*qty
            running += unit*qty
        alloc.allocated_budget = round(alloc_total,2)
        alloc.items = items
        allocations.append(alloc)
    result.allocations = allocations
    result.remaining_budget = round(max(0,budget-running),2)
    return result

def _fallback_home(p: HomeInput):
    b=p.total_budget
    allocations=[]
    lighting_budget=b*.25 if p.lighting_requirements else 0
    fan_budget=b*.25 if p.ceiling_fan_requirements else 0
    furniture_budget=b*.35 if p.furniture_requirements or p.table_quantity else 0
    decor_budget=max(0,b-lighting_budget-fan_budget-furniture_budget)
    if lighting_budget: allocations.append({"category":"Lighting","allocated_budget":lighting_budget,"items":[_item("LED Bulb (Warm White)","Energy-efficient lighting for general room use.",min(500,lighting_budget),max(1,p.lighting_requirements),"Lighting","Amazon")]})
    if fan_budget: allocations.append({"category":"Ceiling Fans","allocated_budget":fan_budget,"items":[_item("Energy Efficient Ceiling Fan","Basic functional ceiling fan option.",min(1800,fan_budget),max(1,p.ceiling_fan_requirements),"Ceiling Fans","Flipkart")]})
    if furniture_budget: allocations.append({"category":"Furniture","allocated_budget":furniture_budget,"items":[_item("Compact Table","Simple table suitable for dining or side use.",min(3500,furniture_budget),max(1,p.table_quantity or 1),"Furniture","IKEA")]})
    if decor_budget: allocations.append({"category":"Decor","allocated_budget":decor_budget,"items":[_item("Wall Art Set","Simple decorative accent for the selected room.",min(1200,decor_budget),1,"Decor","Amazon")]})
    if not allocations: allocations=[{"category":"Essentials","allocated_budget":b,"items":[_item("Budget Starter Set","A basic starter recommendation based on your room details.",min(1000,b),1,"Essentials","Amazon")]}]
    return _normalize({"planner_type":"home","total_budget":b,"allocations":allocations,"remaining_budget":0,"additional_suggestions":["Prioritize essential items first.","Compare search results across platforms before buying.","Keep a small buffer for delivery or installation costs."],"data_notice":"Fallback demo recommendations are shown because a live Gemini response was unavailable."},"home",b)

def _fallback_party(p: PartyInput):
    b=p.total_budget; cats=[]
    enabled=[("Catering",.5,"Swiggy","Catering package"),("Venue",.2,"OYO","Budget-friendly venue/accommodation search"),("Decoration",.15,"Amazon","Party decoration set"),("Entertainment",.15,"Amazon","Portable party speaker")]
    total=sum(x[1] for x in enabled if (x[0]=="Catering" and p.catering) or (x[0]=="Decoration" and p.decoration) or (x[0]=="Entertainment" and p.entertainment) or x[0]=="Venue")
    for cat,ratio,plat,name in enabled:
        if cat=="Catering" and not p.catering or cat=="Decoration" and not p.decoration or cat=="Entertainment" and not p.entertainment: continue
        alloc=b*(ratio/total)
        cats.append({"category":cat,"allocated_budget":alloc,"items":[_item(name,f"Demo option for {p.event_type} with {p.guests} guests.",min(alloc,max(500,alloc)),1,cat,plat)]})
    return _normalize({"planner_type":"party","total_budget":b,"allocations":cats,"remaining_budget":0,"additional_suggestions":["Confirm venue capacity before booking.","Compare per-guest catering rates.","Keep a contingency buffer for last-minute needs."],"data_notice":"Fallback demo recommendations are shown because a live Gemini response was unavailable."},"party",b)

def _fallback_jewelry(p: JewelryInput):
    b=p.budget
    return _normalize({"planner_type":"jewelry","total_budget":b,"allocations":[{"category":"Jewelry","allocated_budget":b*.7,"items":[_item("Classic Jewelry Set",f"Style-matched demo suggestion for {p.occasion}; preference: {p.style_preference or 'versatile'}.",min(b*.7,2500),1,"Jewelry","Amazon")]},{"category":"Accessories","allocated_budget":b*.15,"items":[_item("Matching Earrings","Coordinates with a broad range of outfit colors.",min(b*.15,800),1,"Accessories","Flipkart")]}],"remaining_budget":0,"additional_suggestions":["Match metal tone with the outfit and occasion.","Use the image as a style/color reference, not as an identity source.","Compare prices before purchase."],"data_notice":"Fallback demo recommendations are shown because a live Gemini response was unavailable."},"jewelry",b)

def generate_home(p):
    raw=_generate_with_gemini("home",p.model_dump())
    return _normalize(raw,"home",p.total_budget) if raw else _fallback_home(p)

def generate_party(p):
    raw=_generate_with_gemini("party",p.model_dump())
    return _normalize(raw,"party",p.total_budget) if raw else _fallback_party(p)

def generate_jewelry(p, image_bytes=None, mime_type=None):
    raw=_generate_with_gemini("jewelry",p.model_dump(),image_bytes,mime_type)
    return _normalize(raw,"jewelry",p.budget) if raw else _fallback_jewelry(p)
