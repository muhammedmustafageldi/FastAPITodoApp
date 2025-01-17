from fastapi import APIRouter, Depends, Query, HTTPException
from starlette import status
from models import Todo
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from requests import TodoRequest

router = APIRouter(
    prefix="/todo",
    tags=["Todo"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Db_Dependency = Annotated[Session, Depends(get_db)]

@router.get("/get_all_todos")
async def get_all_data(db: Db_Dependency):
    return db.query(Todo).all()


@router.get("/get_one_todo_by_id/", status_code = status.HTTP_200_OK)
async def get_one_by_id(db: Db_Dependency, id: int = Query(gt=0)):
    todo = db.query(Todo).filter(Todo.id == id).first()
    if todo is not None:
        return todo
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo is not found.")


@router.post("/create/", status_code=status.HTTP_201_CREATED)
async def create_todo(db: Db_Dependency, todo_request: TodoRequest):
    try:
        todo = Todo(**todo_request.model_dump())
        db.add(todo)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/update/", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(db: Db_Dependency, todo_request: TodoRequest, id: int = Query(gt=0)):
    todo = db.query(Todo).filter(Todo.id == id).first()
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
async def delete_todo(db: Db_Dependency, id: int = Query(gt=0)):
    todo = db.query(Todo).filter(Todo.id == id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")
    else:
        db.delete(todo)
        db.commit()