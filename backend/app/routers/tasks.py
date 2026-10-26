# project/starter/app/routers/tasks.py
# Module 5 Project — Task endpoints (auth-scoped)
#

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.exceptions import NotFoundException
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskPatch, TaskResponse

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def log_task_activity(task_id: int, action: str) -> None:
    """
    Record task activity without delaying the API response.
    Scheduled to run after the response.
    """
    logger.info("task_id=%s action=%s", task_id, action)


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=201,
    responses={
        422: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
    },
    summary="Create a new task"
    """When the client send a POST request, run the create_task function.""",
)
def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new task for the authenticated user.

    The task is associated with the currently logged-in user. The **priority** field
    accepts: low, medium, high, or critical (defaults to medium).
    """
    task_data = Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        completed=task.completed,
        owner_id=current_user.id,  # Associate the task with the current user's ID
    )

    db.add(task_data)  # Add the new task to the database session
    db.commit()  # Commit the transaction to save the task in the database permanently
    db.refresh(
        task_data
    )  # Refresh the task_data instance to get the updated data from the database, including the auto-generated id.

    background_tasks.add_task(log_task_activity, task_data.id, "created")

    return task_data  # Return the newly created task data as the response


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    completed: bool | None = Query(default=None),
    priority: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all tasks for the authenticated user.

    Returns a list of tasks associated with the currently logged-in user.
    """
    query = db.query(Task).filter(Task.owner_id == current_user.id)
    if completed is not None:
        query = query.filter(Task.completed == completed)
    if priority is not None:
        query = query.filter(Task.priority == priority)

    tasks = query.offset(skip).limit(limit).all()
    return tasks  # Return the list of tasks as the response


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return one of the current user's needs."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise NotFoundException("Task not found")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this task")
    return task  # Return the task data as the response


@router.patch("/{task_id}", response_model=TaskResponse)
def patch_task(
    task_id: int, task_data: TaskPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Partially update one of the current user's needs."""
    patched_task = db.query(Task).filter(Task.id == task_id).first()
    if not patched_task:
        raise NotFoundException("Task not found")
    if patched_task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this task")

    update_data = task_data.model_dump(exclude_unset=True)  # Get the fields that were provided in the request body
    for key, value in update_data.items():
        setattr(patched_task, key, value)  # Update the task attributes with the provided values
    db.commit()  # Commit the transaction to save the changes in the database
    db.refresh(patched_task)  # Refresh the patched_task instance to get the updated data from the database

    return patched_task  # Return the patched task data as the response


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete one of the current user's needs."""
    task_to_delete = db.query(Task).filter(Task.id == task_id).first()
    if not task_to_delete:
        raise NotFoundException("Task not found")
    if task_to_delete.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this task")

    db.delete(task_to_delete)  # Delete the task from the database session
    db.commit()  # Commit the transaction to remove the task from the database

    return {"detail": "Task deleted successfully"}  # Return a success message as the response


@router.post("/{task_id}/suggest")
def suggest_task_action(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Suggest an action for a specific task based on its details.
    This endpoint is intended to provide suggestions for task actions based on the task's details.
    The suggestion logic can be implemented using AI or other algorithms in the future.

    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise NotFoundException("Task not found")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this task")

    # Placeholder for AI suggestion logic
    suggestion = f"Consider prioritizing this task: {task.title} becasue of the following logical analysis:..."

    return {"suggestion": suggestion}  # Return the suggestion as the response
