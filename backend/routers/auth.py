
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from core.database import get_db
from core.security import create_access_token, decode_access_token
from models.team import Team

router  = APIRouter(prefix='/auth', tags=['auth'])
bearer  = HTTPBearer()
pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')

class LoginRequest(BaseModel):
    team_code: str
    password:  str

class TeamOut(BaseModel):
    id: int
    team_code: str
    name: str
    domain: str
    cash: int
    revenue: int
    market_share: int
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    team: TeamOut

def get_current_team(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
) -> Team:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired token')
    team = db.query(Team).filter(Team.id == int(payload.get('sub'))).first()
    if not team or not team.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Team not found')
    return team

@router.post('/login', response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.team_code == body.team_code.upper()).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid team code')
    if not body.password == team.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid team code or password')
    if not team.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Team account is inactive')
    token = create_access_token({'sub': str(team.id)})
    return LoginResponse(access_token=token, team=TeamOut.model_validate(team))

@router.get('/me', response_model=TeamOut)
def get_me(current_team: Team = Depends(get_current_team)):
    return current_team
