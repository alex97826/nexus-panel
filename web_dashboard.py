import os
import requests
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
# Секретный ключ для сессий браузера
app.add_middleware(SessionMiddleware, secret_key="super-secret-nexus-key-change-me")

templates = Jinja2Templates(directory="templates")

# Твой ID администратора в Discord (строкой)
ADMIN_DISCORD_ID = "815190078442831903"

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8000/callback"
DISCORD_API_URL = "https://discord.com/api/v10"

faq_list = [
    {
        "question": "Как поставить бота на свой сервер?",
        "answer": "Пригласите бота через кнопку авторизации, подтвердите права администратора, и Nexus автоматически подключится к серверу."
    },
    {
        "question": "Какое краткое определение можно дать боту Nexus?",
        "answer": "Nexus — многофункциональный бот с модульной архитектурой, глубокой кастомизацией и моментальной настройкой через веб-дашборд."
    },
    {
        "question": "Бесплатен ли функционал?",
        "answer": "Базовые модули и защита доступны бесплатно и навсегда без ограничений."
    }
]


def get_user_context(request: Request):
    user = request.session.get("user")
    is_admin = bool(user and str(user.get("id")) == str(ADMIN_DISCORD_ID))
    return {"user": user, "is_admin": is_admin}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    ctx = get_user_context(request)
    return templates.TemplateResponse(request, "index.html", ctx)


@app.get("/servers", response_class=HTMLResponse)
async def servers(request: Request):
    ctx = get_user_context(request)
    return templates.TemplateResponse(request, "servers.html", ctx)


@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    ctx = get_user_context(request)
    ctx["faq"] = faq_list
    return templates.TemplateResponse(request, "faq.html", ctx)


@app.post("/add-faq")
async def add_faq(request: Request, question: str = Form(...), answer: str = Form(...)):
    ctx = get_user_context(request)
    if not ctx["is_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещен: добавление доступно только владельцу")

    faq_list.append({"question": question, "answer": answer})
    return RedirectResponse(url="/faq", status_code=303)


@app.get("/login")
async def login():
    if not CLIENT_ID:
        # Режим заглушки для локального тестирования без OAuth2
        return RedirectResponse(url="/mock-login")
    
    redirect_url = os.getenv("DISCORD_REDIRECT_URI", "https://nexus-panel-l46s.onrender.com/callback")
    
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={redirect_url}&response_type=code&scope=identify%20guilds"
    )
    return RedirectResponse(url=discord_auth_url)


@app.get("/mock-login")
async def mock_login(request: Request):
    # Тестовый вход как администратор для проверки интерфейса
    request.session["user"] = {
        "id": ADMIN_DISCORD_ID,
        "username": "Admin",
        "avatar": None
    }
    return RedirectResponse(url="/faq")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/callback")
async def callback(request: Request, code: str):
    redirect_url = os.getenv("DISCORD_REDIRECT_URI", "https://nexus-panel-l46s.onrender.com/callback")
    
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_url,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post(f"{DISCORD_API_URL}/oauth2/token", data=data, headers=headers).json()
    access_token = token_resp.get("access_token")

    if not access_token:
        print("Ошибка получения access_token:", token_resp)
        return RedirectResponse(url="/", status_code=303)

    user_resp = requests.get(
        f"{DISCORD_API_URL}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    request.session["user"] = user_resp
    return RedirectResponse(url="/faq", status_code=303)
    
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_dashboard:app", host="127.0.0.1", port=8000, reload=True)
