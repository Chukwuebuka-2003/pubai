from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from config import JWT_SECRET, JWT_ALGORITHM
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")

        # added a print statement to explicitly show the extracted username
        print(f"Backend (get_current_user): Extracted username from token 'sub' claim: {username}")

        if username is None:
            print("Backend (get_current_user): Token payload 'sub' claim is missing or None.") # Diagnostic
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return username
    except jwt.PyJWTError as e:
        print(f"Backend (get_current_user): JWT decoding error: {e}") # Diagnostic
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
