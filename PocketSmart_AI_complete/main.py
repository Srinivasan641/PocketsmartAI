import json
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from config import settings
from database import init_db, create_user, get_user_by_username, get_user_by_email, create_session, revoke_session, create_recommendation, get_recommendations, get_recommendation
from auth import hash_password, verify_password, create_access_token, decode_token, get_current_user, get_token_from_request
from schemas import RegisterInput, LoginInput, HomeInput, PartyInput, JewelryInput
from gemini_utils import generate_home, generate_party, generate_jewelry

BASE=Path(__file__).resolve().parent
UPLOAD_DIR=BASE/"static"/"uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app=FastAPI(title="PocketSmart AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE/"static"), name="static")
templates=Jinja2Templates(directory=BASE/"templates")

@app.on_event("startup")
def startup(): init_db()

def render(request, name, **ctx):
    return templates.TemplateResponse(request=request, name=name, context=ctx)

def set_auth_cookie(response, token):
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=settings.access_token_expire_minutes*60)

def clear_auth_cookie(response): response.delete_cookie("access_token")

def user_dict(user): return {"id":user["id"],"username":user["username"],"email":user["email"]}

@app.get("/", response_class=HTMLResponse)
def home(request: Request): return render(request,"index.html",user=None)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request): return render(request,"register.html")

@app.post("/register")
def register(payload: RegisterInput):
    if payload.password != payload.confirm_password: raise HTTPException(400,"Passwords do not match.")
    if get_user_by_username(payload.username): raise HTTPException(409,"Username already exists.")
    if get_user_by_email(payload.email.lower()): raise HTTPException(409,"Email already registered.")
    uid=create_user(payload.username, payload.email.lower(), hash_password(payload.password))
    token,jti,exp=create_access_token(uid); create_session(jti,uid,exp.isoformat())
    r=JSONResponse({"message":"Account created successfully.","user":{"id":uid,"username":payload.username}}); set_auth_cookie(r,token); return r

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return render(request,"login.html")

@app.post("/login")
def login(payload: LoginInput):
    user=get_user_by_username(payload.username)
    if not user or not verify_password(payload.password,user["password_hash"]): raise HTTPException(401,"Invalid username or password.")
    token,jti,exp=create_access_token(user["id"]); create_session(jti,user["id"],exp.isoformat())
    r=JSONResponse({"message":"Login successful.","user":user_dict(user)}); set_auth_cookie(r,token); return r

@app.post("/logout")
def logout(request: Request):
    token=get_token_from_request(request)
    if token:
        try: revoke_session(decode_token(token)["jti"])
        except Exception: pass
    r=JSONResponse({"message":"Logged out."}); clear_auth_cookie(r); return r

@app.post("/token")
def token_alias(payload: LoginInput): return login(payload)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(get_current_user)):
    rows=get_recommendations(user["id"],6)
    return render(request,"dashboard.html",user=user,recent=rows)

@app.get("/home-planner", response_class=HTMLResponse)
def home_planner(request: Request, user=Depends(get_current_user)): return render(request,"home_planner.html",user=user)
@app.get("/party-planner", response_class=HTMLResponse)
def party_planner(request: Request, user=Depends(get_current_user)): return render(request,"party_planner.html",user=user)
@app.get("/jewelry-planner", response_class=HTMLResponse)
def jewelry_planner(request: Request, user=Depends(get_current_user)): return render(request,"jewelry_planner.html",user=user)

@app.post("/generate-home")
def generate_home_route(payload: HomeInput, user=Depends(get_current_user)):
    result=generate_home(payload); rid=create_recommendation(user["id"],"home",json.dumps(payload.model_dump()),result.model_dump_json())
    return {"id":rid,"result":result.model_dump()}

@app.post("/generate-party")
def generate_party_route(payload: PartyInput, user=Depends(get_current_user)):
    result=generate_party(payload); rid=create_recommendation(user["id"],"party",json.dumps(payload.model_dump()),result.model_dump_json())
    return {"id":rid,"result":result.model_dump()}

@app.post("/generate-jewelry")
async def generate_jewelry_route(budget: float=Form(...), occasion: str=Form(...), style_preference: str=Form(""), outfit_description: str=Form(""), image: UploadFile|None=File(None), user=Depends(get_current_user)):
    if budget<=0: raise HTTPException(422,"Budget must be greater than zero.")
    image_bytes=None; mime=None; saved_name=None
    if image and image.filename:
        allowed={"image/jpeg","image/png","image/webp"}
        if image.content_type not in allowed: raise HTTPException(400,"Upload a JPG, PNG, or WEBP image.")
        data=await image.read()
        if len(data)>settings.max_upload_mb*1024*1024: raise HTTPException(400,f"Image must be smaller than {settings.max_upload_mb} MB.")
        ext={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}[image.content_type]
        saved_name=f"{uuid.uuid4().hex}{ext}"; (UPLOAD_DIR/saved_name).write_bytes(data); image_bytes=data; mime=image.content_type
    payload=JewelryInput(budget=budget,occasion=occasion,style_preference=style_preference,outfit_description=outfit_description)
    result=generate_jewelry(payload,image_bytes,mime)
    input_data=payload.model_dump(); input_data["image_uploaded"]=bool(saved_name)
    rid=create_recommendation(user["id"],"jewelry",json.dumps(input_data),result.model_dump_json())
    return {"id":rid,"result":result.model_dump()}

@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, user=Depends(get_current_user)):
    return render(request,"history.html",user=user,history=get_recommendations(user["id"]))

@app.get("/history-data")
def history_data(user=Depends(get_current_user)):
    return {"history":[dict(x) for x in get_recommendations(user["id"])]}

@app.get("/recommendations-details/{recommendation_id}", response_class=HTMLResponse)
def recommendation_details(request: Request, recommendation_id: int, user=Depends(get_current_user)):
    row=get_recommendation(user["id"],recommendation_id)
    if not row: raise HTTPException(404,"Recommendation not found.")
    return render(request,"recommendation_details.html",user=user,record=row,result=json.loads(row["result_json"]),inputs=json.loads(row["input_json"]))

@app.get("/recommendations-details")
def recommendation_details_api(recommendation_id: int, user=Depends(get_current_user)):
    row=get_recommendation(user["id"],recommendation_id)
    if not row: raise HTTPException(404,"Recommendation not found.")
    return {"id":row["id"],"planner_type":row["planner_type"],"input":json.loads(row["input_json"]),"result":json.loads(row["result_json"])}

@app.get("/session-info")
def session_info(request: Request, user=Depends(get_current_user)):
    return {"authenticated":True,"user":user_dict(user)}

@app.get("/session-data")
def session_data(request: Request, user=Depends(get_current_user)):
    rows=get_recommendations(user["id"],10)
    return {"user":user_dict(user),"recommendation_count":len(rows),"recent":[{"id":r["id"],"planner_type":r["planner_type"],"created_at":r["created_at"]} for r in rows]}

@app.get("/startup")
def startup_status(): return {"status":"ok","app":"PocketSmart AI","gemini_configured":bool(settings.gemini_api_key),"model":settings.gemini_model}

@app.exception_handler(HTTPException)
async def http_error(request, exc):
    if request.url.path.startswith("/generate-") or request.headers.get("accept","").startswith("application/json"):
        return JSONResponse({"error":exc.detail},status_code=exc.status_code)
    return JSONResponse({"error":exc.detail},status_code=exc.status_code)

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app",host="127.0.0.1",port=8000,reload=False)
