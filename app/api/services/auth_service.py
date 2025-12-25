"""
Authentication service for PC Recommendation System
Handles password hashing, JWT token management, and user authentication
"""

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_database
from app.core.logging import get_logger
from app.api.models.user import UserInDB, UserCreate, UserLoginRequest
from app.api.models.auth import TokenData, UserSessionInDB, AuthAuditLog
from bson import ObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for handling user authentication and authorization"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days

    async def authenticate_user(self, email: str, password: str) -> UserInDB:
        """
        Authenticate a user with email and password

        Args:
            email: User's email address
            password: User's password

        Returns:
            UserInDB object if authentication successful

        Raises:
            ValueError: If user not found or invalid password
        """
        try:
            db = await get_database()
            if db is None:
                raise ValueError("database_not_available")
            self.logger.debug(f"Authenticating user: {email}")

            # Find user by email
            user_doc = await db.users.find_one({"email": email.lower()})
            if not user_doc:
                self.logger.warning(f"User not found: {email}")
                raise ValueError("user_not_found")

            # Validate user document has required fields
            if 'password_hash' not in user_doc or not user_doc['password_hash']:
                self.logger.error(f"Invalid user data for {email}: missing password_hash")
                raise ValueError("invalid_user_data")

            # Create user object
            try:
                user = UserInDB(**user_doc)
                self.logger.debug(f"User object created for {email}")
            except Exception as e:
                self.logger.error(f"Failed to create UserInDB object for {email}: {e}")
                raise ValueError("invalid_user_data")

            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                self.logger.warning(f"Account locked for {email} until {user.locked_until}")
                raise ValueError("account_locked")

            # Verify password
            if not self.verify_password(password, user.password_hash):
                self.logger.warning(f"Invalid password for {email}")
                await self._increment_login_attempts(user.id)
                raise ValueError("invalid_password")

            # Reset login attempts on successful login
            await self._reset_login_attempts(user.id)
            self.logger.info(f"User authenticated successfully: {email}")

            # Update last login
            try:
                await db.users.update_one(
                    {"_id": user.id},
                    {"$set": {"last_login": datetime.now(timezone.utc)}}
                )
                self.logger.debug(f"Last login updated for {email}")
            except Exception as e:
                self.logger.error(f"Failed to update last login for {email}: {e}")
                # Don't fail authentication for this

            return user

        except ValueError:
            # Re-raise ValueError as-is (expected authentication errors)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication for {email}: {e}", exc_info=True)
            raise ValueError("service_unavailable")

    async def create_user(self, user_data: UserCreate) -> UserInDB:
            db = await get_database()

            email = user_data.email.lower().strip()

            existing_user = await db.users.find_one({"email": email})
            if existing_user:
                    raise ValueError("email_already_exists")

            hashed_password = pwd_context.hash(user_data.password)

            user_doc = {
                    "_id": ObjectId(),
                    "email": email,
                    "full_name": user_data.full_name,
                    "password_hash": hashed_password,  # ✅ correct field
                    "is_active": True,
                    "is_verified": False,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

            await db.users.insert_one(user_doc)   # ✅ INSERT ONCE
            return UserInDB(**user_doc)            # ✅ RETURN USER

    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Comprehensive password strength validation with enhanced security checks

        Args:
            password: Password to validate

        Returns:
            Dict with validation results and detailed feedback
        """
        if not isinstance(password, str):
            return {"valid": False, "errors": ["Password must be a string"]}

        errors = []
        warnings = []
        score = 0
        max_score = 6

        # Length check (enhanced)
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        elif len(password) >= 12:
            score += 2  # Bonus for longer passwords
        else:
            score += 1

        # Character variety checks
        checks = [
            (r'[a-z]', "lowercase letter", 1),
            (r'[A-Z]', "uppercase letter", 1),
            (r'\d', "number", 1),
            (r'[!@#$%^&*(),.?":{}|<>]', "special character", 1),
        ]

        for pattern, description, points in checks:
            if re.search(pattern, password):
                score += points
            else:
                errors.append(f"Password must contain at least one {description}")

        # Length bonus
        if len(password) >= 16:
            score += 1

        # Common password check (expanded)
        common_passwords = [
            'password', '123456', 'qwerty', 'admin', 'letmein', 'welcome',
            'monkey', 'dragon', 'password1', 'qwerty123', 'admin123'
        ]
        if password.lower() in common_passwords:
            errors.append("Password is too common - choose a more unique password")
            score = max(0, score - 2)

        # Sequential patterns check
        if re.search(r'(?:012|123|234|345|456|567|678|789|890)', password):
            warnings.append("Avoid sequential numbers in your password")
            score = max(0, score - 1)

        if re.search(r'(?:abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
            warnings.append("Avoid sequential letters in your password")
            score = max(0, score - 1)

        # Repeated characters check
        if re.search(r'(.)\1{2,}', password):
            warnings.append("Avoid repeated characters")
            score = max(0, score - 1)

        # Strength assessment
        if score >= 5:
            strength = "strong"
        elif score >= 3:
            strength = "medium"
        else:
            strength = "weak"

        # Entropy estimation (basic)
        char_sets = 0
        if re.search(r'[a-z]', password): char_sets += 26
        if re.search(r'[A-Z]', password): char_sets += 26
        if re.search(r'\d', password): char_sets += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password): char_sets += 10

        entropy = len(password) * (char_sets ** 0.5) if char_sets > 0 else 0

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": score,
            "strength": strength,
            "max_score": max_score,
            "entropy": round(entropy, 2),
            "recommendations": self._get_password_recommendations(password)
        }

    def _get_password_recommendations(self, password: str) -> List[str]:
        """Generate personalized password improvement recommendations"""
        recommendations = []

        if len(password) < 12:
            recommendations.append("Consider using at least 12 characters for better security")

        char_checks = [
            (r'[a-z]', "Add lowercase letters"),
            (r'[A-Z]', "Add uppercase letters"),
            (r'\d', "Add numbers"),
            (r'[!@#$%^&*(),.?":{}|<>]', "Add special characters"),
        ]

        for pattern, recommendation in char_checks:
            if not re.search(pattern, password):
                recommendations.append(recommendation)

        if len(recommendations) == 0:
            recommendations.append("Your password meets all basic requirements")

        return recommendations

    def hash_password(self, password: str) -> str:
        """Hash a password using pbkdf2_sha256"""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change a user's password"""
        db = await get_database()

        # Verify current password
        user_doc = await db.users.find_one({"_id": ObjectId(user_id) if isinstance(user_id, str) else user_id})
        if not user_doc or not self.verify_password(current_password, user_doc["password_hash"]):
            return False

        # Hash new password
        hashed_password = self.hash_password(new_password)

        # Update user password
        result = await db.users.update_one(
            {"_id": ObjectId(user_id) if isinstance(user_id, str) else user_id},
            {"$set": {"password_hash": hashed_password, "updated_at": datetime.now(timezone.utc)}}
        )

        return result.modified_count > 0

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "token_type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "token_type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("user_id")
            email: str = payload.get("email")
            exp: datetime = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
            iat: datetime = datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc)
            token_type: str = payload.get("token_type")

            if user_id is None or email is None:
                return None

            return TokenData(
                user_id=user_id,
                email=email,
                exp=exp,
                iat=iat,
                token_type=token_type
            )
        except JWTError:
            return None

    async def create_user_session(self, user_id: Union[str, ObjectId], ip_address: str = None,
                                user_agent: str = None) -> UserSessionInDB:
        """Create a new user session"""
        try:
            self.logger.debug(f"Creating session for user: {user_id}")
            db = await get_database()

            # Create tokens
            try:
                token_data = {"user_id": str(user_id), "email": await self._get_user_email(user_id)}
                if not token_data["email"]:
                    self.logger.error(f"Could not get email for user {user_id}")
                    raise ValueError("user_not_found")
                    
                access_token = self.create_access_token(token_data)
                refresh_token = self.create_refresh_token(token_data)
                self.logger.debug(f"Tokens created for user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to create tokens for user {user_id}: {e}")
                raise

            # Create session document
            session_doc = {
                "user_id": user_id,
                "session_token": access_token,
                "refresh_token": refresh_token,
                "ip_address": ip_address or "unknown",
                "user_agent": user_agent or "unknown",
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes),
                "last_activity": datetime.now(timezone.utc),
                "is_active": True
            }

            # Insert session
            try:
                result = await db.user_sessions.insert_one(session_doc)
                session_doc["_id"] = result.inserted_id
                self.logger.debug(f"Session created in database for user {user_id}")
            except Exception as e:
                self.logger.error(f"Failed to insert session for user {user_id}: {e}")
                raise

            # Create session object
            try:
                session = UserSessionInDB(**session_doc)
                self.logger.info(f"Session created successfully for user {user_id}")
                return session
            except Exception as e:
                self.logger.error(f"Failed to create UserSessionInDB object for user {user_id}: {e}")
                raise

        except Exception as e:
            self.logger.error(f"Unexpected error creating session for user {user_id}: {e}", exc_info=True)
            raise

    async def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a user session"""
        db = await get_database()

        result = await db.user_sessions.update_one(
            {"session_token": session_token},
            {"$set": {"is_active": False}}
        )

        return result.modified_count > 0

    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh an access token using a refresh token"""
        db = await get_database()

        # Find session with refresh token
        session_doc = await db.user_sessions.find_one({
            "refresh_token": refresh_token,
            "is_active": True
        })

        if not session_doc:
            return None

        session = UserSessionInDB(**session_doc)

        # Check if refresh token is expired
        if session.expires_at < datetime.now(timezone.utc):
            return None

        # Create new access token
        token_data = {"user_id": str(session.user_id), "email": await self._get_user_email(str(session.user_id))}
        new_access_token = self.create_access_token(token_data)

        # Update session
        await db.user_sessions.update_one(
            {"_id": session.id},
            {
                "$set": {
                    "session_token": new_access_token,
                    "last_activity": datetime.now(timezone.utc)
                }
            }
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }

    async def _increment_login_attempts(self, user_id: str):
        """Increment failed login attempts for a user"""
        db = await get_database()

        # Increment attempts
        await db.users.update_one(
            {"_id": user_id},
            {"$inc": {"login_attempts": 1}}
        )

        # Check if account should be locked (5+ attempts)
        user_doc = await db.users.find_one({"_id": user_id})
        if user_doc and user_doc.get("login_attempts", 0) >= 5:
            # Lock account for 15 minutes
            locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await db.users.update_one(
                {"_id": user_id},
                {"$set": {"locked_until": locked_until}}
            )

    async def _reset_login_attempts(self, user_id: str):
        """Reset login attempts for a user"""
        db = await get_database()

        await db.users.update_one(
            {"_id": user_id},
            {"$set": {"login_attempts": 0, "locked_until": None}}
        )

    async def _get_user_email(self, user_id) -> str:
        """Get user email by ID"""
        db = await get_database()
        user_id_obj = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        user_doc = await db.users.find_one({"_id": user_id_obj})
        return user_doc["email"] if user_doc else ""

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login a user and create a session

        Args:
            email: User's email
            password: User's password

        Returns:
            Dict with access_token, refresh_token, user info, etc.

        Raises:
            ValueError: If authentication fails
        """
        try:
            # Authenticate user
            user = await self.authenticate_user(email, password)
            
            # Create session
            session = await self.create_user_session(user.id)
            
            return {
                "access_token": session.session_token,
                "refresh_token": session.refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                    "last_login": user.last_login
                }
            }
        except ValueError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during login for {email}: {e}", exc_info=True)
            raise ValueError("service_unavailable")


# Global auth service instance
auth_service = AuthService()
