from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from passlib.hash import bcrypt

from .models import User, Role, TgSession, Meeting, Question


# -------------------- users --------------------

async def create_user(db: AsyncSession, username: str, password: str, role_id: int) -> User:
    # u = User(username=username, password_hash=bcrypt.hash(password), role_id=role_id)
    u = User(username=username, password_hash=password, role_id=role_id)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    result = await db.execute(
        select(User).options(joinedload(User.role)).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    # if user and bcrypt.verify(password, user.password_hash):
    #     return user
    if user and password == user.password_hash:
        return user
    return None


async def set_active_session(db: AsyncSession, telegram_id: int, user_id: int) -> TgSession:
    await db.execute(update(TgSession).where(TgSession.telegram_id == telegram_id).values(is_active=False))
    s = TgSession(telegram_id=telegram_id, user_id=user_id, is_active=True)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_active_user(db: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(joinedload(User.role))
        .join(TgSession, TgSession.user_id == User.id)
        .where(TgSession.telegram_id == telegram_id, TgSession.is_active == True)
    )
    return result.scalar_one_or_none()


async def logout(db: AsyncSession, telegram_id: int):
    await db.execute(update(TgSession).where(TgSession.telegram_id == telegram_id).values(is_active=False))
    await db.commit()



# -------------------- roles --------------------

async def list_roles(db: AsyncSession) -> List[Role]:
    return (await db.execute(select(Role).order_by(Role.id))).scalars().all()


async def create_role(db: AsyncSession, name: str) -> Role:
    r = Role(name=name)
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def rename_role(db: AsyncSession, role_id: int, new_name: str):
    await db.execute(update(Role).where(Role.id == role_id).values(name=new_name))
    await db.commit()


async def delete_role(db: AsyncSession, role_id: int) -> bool:
    used = (await db.execute(select(User).where(User.role_id == role_id))).scalars().first()
    if used:
        return False
    await db.execute(delete(Role).where(Role.id == role_id))
    await db.commit()
    return True


async def set_user_role(db: AsyncSession, username: str, role_id: int) -> bool:
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if not user:
        return False
    await db.execute(update(User).where(User.id == user.id).values(role_id=role_id))
    await db.commit()
    return True


# -------------------- meetings --------------------

from datetime import datetime
from .models import Meeting

async def create_meeting(
    db,
    title: str,
    description: str,
    department: str,
    country: str,
    deadline_at,
    created_by: int
):
    """Создание новой встречи"""
    meeting = Meeting(
        title=title.strip(),
        description=description.strip(),
        department=department.strip(),
        country=country.strip(),
        deadline_at=deadline_at,
        status="draft",
        created_by=created_by,
        created_at=datetime.utcnow(),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting



async def list_meetings(db: AsyncSession) -> List[Meeting]:
    return (await db.execute(select(Meeting).order_by(Meeting.id))).scalars().all()


async def set_meeting_status(db: AsyncSession, meeting_id: int, status: str) -> bool:
    res = await db.execute(update(Meeting).where(Meeting.id == meeting_id).values(status=status))
    await db.commit()
    return res.rowcount > 0


async def delete_meeting(db: AsyncSession, meeting_id: int) -> bool:
    res = await db.execute(delete(Meeting).where(Meeting.id == meeting_id))
    await db.commit()
    return res.rowcount > 0


async def add_question(db: AsyncSession, meeting_id: int, text: str) -> Optional[Question]:
    meeting = (await db.execute(select(Meeting).where(Meeting.id == meeting_id))).scalar_one_or_none()
    if not meeting:
        return None
    q = Question(meeting_id=meeting_id, text=text)
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q

from .models import Question, Answer

# список вопросов встречи
async def list_questions(db: AsyncSession, meeting_id: int) -> list[Question]:
    result = await db.execute(
        select(Question).where(Question.meeting_id == meeting_id).order_by(Question.order_idx)
    )
    return result.scalars().all()

# добавить ответ пользователя
from .models import Answer, Response
from datetime import datetime

async def add_answer(db: AsyncSession, user_id: int, question_id: int, text: str) -> Answer:
    """Добавляет ответ пользователя на вопрос (через Response)."""
    # определяем встречу через вопрос
    question = (await db.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    if not question:
        return None

    # находим или создаём response для этого пользователя и встречи
    response = (await db.execute(
        select(Response)
        .where(Response.user_id == user_id, Response.meeting_id == question.meeting_id)
    )).scalar_one_or_none()

    if not response:
        response = Response(user_id=user_id, meeting_id=question.meeting_id, status="draft", submitted_at=datetime.utcnow())
        db.add(response)
        await db.flush()  # чтобы получить response.id без commit

    # создаём ответ
    answer = Answer(
        response_id=response.id,
        question_id=question_id,
        value=text.strip(),
    )
    db.add(answer)
    await db.commit()
    await db.refresh(answer)
    return answer

