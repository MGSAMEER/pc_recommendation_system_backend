from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.models.user import UserSignupRequest, UserLoginRequest
from app.api.services.auth_service import auth_service
from app.api.services.user_service import user_service
from app.api.models.auth import ChangePasswordRequest

router = APIRouter()
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


# ------------------------
# SIGNUP
# ------------------------
@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    summary="User signup"
)
async def signup(user_data: UserSignupRequest):
    try:
        user = await auth_service.create_user(user_data)
        return {
            "message": "Signup successful",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ------------------------
# LOGIN
# ------------------------
@router.post(
    "/signin",
    status_code=status.HTTP_200_OK,
    summary="User signin"
)
@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="User login (compat)"
)
async def signin(login_data: UserLoginRequest):
    try:
        result = await auth_service.login(
            login_data.email,
            login_data.password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


# ------------------------
# ME
# ------------------------
@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get current user"
)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    try:
        user = await user_service.get_user_profile(current_user.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login": user.last_login
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


# ------------------------
# PASSWORD CHANGE
# ------------------------
@router.put(
    "/password",
    status_code=status.HTTP_200_OK,
    summary="Change user password"
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change user password"""
    try:
        # Validate new password strength
        strength_result = auth_service.validate_password_strength(password_data.new_password)
        if not strength_result["is_strong"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password too weak: {', '.join(strength_result['issues'])}"
            )

        # Change password
        success = await auth_service.change_password(
            current_user.user_id,
            password_data.current_password,
            password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
