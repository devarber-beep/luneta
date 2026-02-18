from datetime import datetime, timedelta
from typing import Any, Optional

from jose import jwt

from .settings import settings


ALGORITHM = "HS256"


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    # NOTE: for now reuse ai_model as dummy secret; replace with dedicated secret
    secret_key = settings.ai_model
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt

