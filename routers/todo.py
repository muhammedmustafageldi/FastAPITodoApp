from fastapi import APIRouter, Depends, Query, HTTPException, Request
from starlette import status
from starlette.responses import RedirectResponse
from ..models import Todo
from ..db.database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from ..model_request import TodoRequest
from ..routers.auth import get_current_user
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import markdown
from bs4 import BeautifulSoup

router = APIRouter(
    prefix="/todo",
    tags=["Todo"]
)

templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Db_Dependency = Annotated[Session, Depends(get_db)]
User_dependency = Annotated[dict, Depends(get_current_user)]


def redirect_to_login_page():
    redirect_response = RedirectResponse(url="/auth/login_page", status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie('access_token')
    return redirect_response


@router.get("/todo_page")
async def render_todo_page(request: Request, db: Db_Dependency):
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login_page()
        role = user.get('user_role')

        if role == 'admin':
            todos = db.query(Todo).all()
        else:
            todos = db.query(Todo).filter(Todo.owner_id == user.get('user_id')).all()
        return templates.TemplateResponse("todo.html", {"request": request, "todos": todos, "user": user})
    except Exception as e:
        print(e)
        return redirect_to_login_page()


@router.get("/add_todo_page")
async def render_add_todo_page(request: Request):
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login_page()
        return templates.TemplateResponse("add_todo.html", {"request": request, "user": user})
    except Exception as e:
        print(e)
        return redirect_to_login_page()


@router.get("/edit_todo_page/{todo_id}")
async def render_edit_todo_page(request: Request, todo_id: int,db: Db_Dependency):
    try:
        user = await get_current_user(request.cookies.get('access_token'))
        if user is None:
            return redirect_to_login_page()
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        return templates.TemplateResponse("edit_todo.html", {"request": request, "todo":todo, "user": user})
    except Exception as e:
        print(e)
        return redirect_to_login_page()


@router.get("/")
async def get_all_data(user: User_dependency ,db: Db_Dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    role = user.get('user_role')

    if role == 'admin':
        return db.query(Todo).all()
    return db.query(Todo).filter(Todo.owner_id == user.get('user_id')).all()


@router.get("/todo/", status_code = status.HTTP_200_OK)
async def get_one_by_id(user: User_dependency,db: Db_Dependency, todo_id: int = Query(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('user_id')).first()
    if todo is not None:
        return todo
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo is not found.")


@router.post("/create/", status_code=status.HTTP_201_CREATED)
async def create_todo(user: User_dependency ,db: Db_Dependency, todo_request: TodoRequest, use_ai: bool = Query(False)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        todo = Todo(**todo_request.model_dump(), owner_id=user.get('user_id'))
        if use_ai:
            todo.description = await create_todo_with_gemini(todo.title)
        db.add(todo)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/update/", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: User_dependency,db: Db_Dependency, todo_request: TodoRequest, todo_id: int = Query(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('user_id')).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")
    else:
        todo.title = todo_request.title
        todo.description = todo_request.description
        todo.priority = todo_request.priority
        todo.is_completed = todo_request.is_completed

        db.add(todo)
        db.commit()


@router.delete("/delete/", status_code=status.HTTP_200_OK)
async def delete_todo(user: User_dependency ,db: Db_Dependency, todo_id: int = Query(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if user.get('user_role') == 'admin':
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
    else:
        todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get('user_id')).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")
    else:
        db.delete(todo)
        db.commit()


def markdown_to_text(markdown_string: str):
    html = markdown.markdown(markdown_string)
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()


async def create_todo_with_gemini(todo_string: str):
    load_dotenv()
    genai.configure(api_key=os.environ.get("API_KEY"))
    llm = ChatGoogleGenerativeAI(model="gemini-pro")
    response = llm.invoke(
        [
            HumanMessage("I'm going to give you a to-do item to add to my to-do list. What I want you to do is to create a slightly more elaborated version of this to-do item, but not too long. My next message will be my to-do item: "),
            HumanMessage(content=todo_string)
        ]
    )
    return markdown_to_text(response.content)