from sqlalchemy.orm import Session

from app.db.tables import HumanFlag


def flag_for_human(user_id: str, session_id: str, reason: str, db: Session) -> None:
    db.add(HumanFlag(user_id=user_id, session_id=session_id, reason=reason))
    db.commit()
