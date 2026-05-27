"""
ARCX Auth Views — Phase 6
---------------------------
Goes in: arcx_backend/arcx_core/views/auth_views.py

Endpoints:
  POST /api/v1/auth/register  -> Create account + return JWT immediately
  GET  /api/v1/auth/me        -> Authenticated user's full profile
  POST /api/v1/auth/logout    -> Blacklist refresh token

DESIGN: Register returns tokens immediately.
  Most apps make users register then separately log in.
  That's two round trips. ARCX registers + logs in atomically.
  The user gets their JWT on the same response as account creation.
  Smoother UX, fewer failure points.

LOGOUT APPROACH:
  JWT is stateless - the server can't "revoke" an access token.
  The access token expires in 30 minutes naturally.
  To truly log out, we blacklist the refresh token so no new
  access tokens can be minted. The current access token becomes
  useless within 30 min max.

  This requires: rest_framework_simplejwt.token_blacklist in INSTALLED_APPS
  and running: python manage.py migrate
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, serializers as drf_serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
)

from arcx_core.serializers_auth import (
    RegisterRequestSerializer,
    RegisterResponseSerializer,
    UserProfileSerializer,
    LogoutRequestSerializer,
)
from arcx_core.services.auth_service import AuthService, RegistrationError
from arcx_core.exceptions import arcx_exception_handler

logger = logging.getLogger("arcx.views.auth")

# -- Shared inline error schema ------------------------------------------------
_ErrorSchema = inline_serializer(
    name="ErrorResponse",
    fields={
        "error": drf_serializers.CharField(help_text="Human-readable error message"),
        "code":  drf_serializers.CharField(help_text="Machine-readable snake_case error code"),
    },
)


class RegisterView(APIView):
    """
    POST /api/v1/auth/register

    Body:
      {
        "email":     "user@example.com",
        "password":  "securepassword123",
        "full_name": "Rahul Sharma",
        "phone":     "+91 98765 43210"   <- optional
      }

    Response:
      {
        "user_id":       "uuid...",
        "email":         "user@example.com",
        "full_name":     "Rahul Sharma",
        "kyc_status":    "pending",
        "access_token":  "eyJ...",
        "refresh_token": "eyJ...",
        "message":       "Account created. Complete KYC to start transacting."
      }
    """
    permission_classes = [AllowAny]   # Registration requires no prior auth

    @extend_schema(
        tags=["Auth"],
        operation_id="auth_register",
        summary="Register a new account",
        description=(
            "Creates a new ARCX user account and immediately returns JWT tokens "
            "so the user is logged in on the same request — no separate login step required.\n\n"
            "**KYC Note:** New accounts start with `kyc_status=pending`. "
            "Deposit, withdraw, and transfer all require KYC approval."
        ),
        request=RegisterRequestSerializer,
        responses={
            201: RegisterResponseSerializer,
            409: OpenApiResponse(
                response=_ErrorSchema,
                description="Email already registered",
                examples=[
                    OpenApiExample(
                        "Email conflict",
                        value={"error": "An account with this email already exists.", "code": "REGISTRATION_FAILED"},
                    )
                ],
            ),
            400: OpenApiResponse(response=_ErrorSchema, description="Validation error — check field format"),
        },
        examples=[
            OpenApiExample(
                "Typical registration",
                request_only=True,
                value={
                    "email":     "rahul@example.com",
                    "password":  "MyStr0ng#Pass",
                    "full_name": "Rahul Sharma",
                    "phone":     "+91 98765 43210",
                },
            ),
        ],
        auth=[],   # Public — no Bearer token required
    )
    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            service   = AuthService()
            arcx_user = service.register(
                email     = data["email"],
                password  = data["password"],
                full_name = data["full_name"],
                phone     = data.get("phone"),
            )
        except RegistrationError as e:
            return Response(
                {"error": str(e), "code": "REGISTRATION_FAILED"},
                status=status.HTTP_409_CONFLICT,
            )

        # Issue JWT tokens immediately -- user is logged in on registration
        # We need the auth.User that was created by the service
        from django.contrib.auth.models import User as AuthUser
        auth_user = AuthUser.objects.get(username=str(arcx_user.id))
        refresh   = RefreshToken.for_user(auth_user)

        logger.info("New registration: user_id=%s email=%s", arcx_user.id, arcx_user.email)

        return Response(
            {
                "user_id":       str(arcx_user.id),
                "email":         arcx_user.email,
                "full_name":     arcx_user.full_name,
                "kyc_status":    arcx_user.kyc_status,
                "access_token":  str(refresh.access_token),
                "refresh_token": str(refresh),
                "message":       "Account created. Complete KYC to start transacting.",
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """
    GET /api/v1/auth/me

    Returns the authenticated user's full profile.
    Includes wallet balance and KYC status -- everything a dashboard
    home screen needs in one call.

    No KYC requirement -- even pending users can see their profile.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        operation_id="auth_me",
        summary="Get current user profile",
        description=(
            "Returns the authenticated user's full profile, including wallet balance "
            "and KYC tier. One call gives everything the dashboard home screen needs."
        ),
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(response=_ErrorSchema, description="Missing or invalid JWT"),
        },
    )
    def get(self, request):
        user_id = request.user.username   # JWT sub = ARCX User UUID

        service   = AuthService()
        arcx_user = service.get_arcx_user(user_id)

        serializer = UserProfileSerializer(arcx_user)
        data = serializer.data
        data["is_staff"] = request.user.is_staff
        return Response(data)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout

    Body:
      { "refresh_token": "eyJ..." }

    Blacklists the refresh token. Requires:
      INSTALLED_APPS += ["rest_framework_simplejwt.token_blacklist"]
      python manage.py migrate
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        operation_id="auth_logout",
        summary="Logout (blacklist refresh token)",
        description=(
            "Blacklists the provided refresh token so it can't mint new access tokens. "
            "The current access token still works until its 30-minute TTL expires — "
            "this is by design with stateless JWT architecture."
        ),
        request=LogoutRequestSerializer,
        responses={
            200: inline_serializer(
                name="LogoutSuccess",
                fields={"message": drf_serializers.CharField()},
            ),
            400: OpenApiResponse(response=_ErrorSchema, description="Invalid or already-blacklisted token"),
            401: OpenApiResponse(response=_ErrorSchema, description="Missing or invalid JWT"),
        },
        examples=[
            OpenApiExample(
                "Logout request",
                request_only=True,
                value={"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
            ),
        ],
    )
    def post(self, request):
        serializer = LogoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh_token"])
            token.blacklist()
            logger.info("Logout: user=%s token blacklisted", request.user.username)
            return Response(
                {"message": "Logged out successfully."},
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            return Response(
                {"error": "Invalid or expired refresh token.", "code": "INVALID_TOKEN"},
                status=status.HTTP_400_BAD_REQUEST,
            )

import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from arcx_core.models import OTPVerification
from arcx_core.services.b2b_service import B2BService
from arcx_core.serializers_auth import ResetPinRequestSerializer

class ForgotPinView(APIView):
    """
    POST /api/v1/auth/forgot-pin
    Generates a 6-digit OTP and sends it via email.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Forgot PIN (Send OTP)",
        responses={200: inline_serializer("ForgotPinSuccess", {"message": drf_serializers.CharField()})}
    )
    def post(self, request):
        user_id = request.user.username
        try:
            from arcx_core.models import User
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found.", "code": "USER_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        
        # Invalidate old OTPs for this purpose
        OTPVerification.objects.filter(user=user, purpose="PIN_RESET", is_used=False).update(is_used=True)
        
        # Generate 6 digit OTP
        otp_code = str(random.randint(100000, 999999))
        
        OTPVerification.objects.create(
            user=user,
            code=otp_code,
            purpose="PIN_RESET",
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        html_content = f"""<div style="background-color: #f5f5f7; padding: 40px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <div style="max-width: 400px; margin: 0 auto; background: #ffffff; border-radius: 32px; padding: 32px; box-shadow: 0 8px 30px rgba(0,0,0,0.04);">
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px;">
            <tr>
                <td align="left">
                    <div style="width: 48px; height: 48px; border-radius: 50%; border: 1px solid #e2e8f0; display: inline-block; text-align: center; line-height: 48px; padding: 4px; box-sizing: border-box;">
                        <div style="width: 100%; height: 100%; background-color: #ef4444; border-radius: 50%; display: inline-block;"></div>
                    </div>
                </td>
                <td align="right">
                    <div style="background-color: #f1f5f9; border-radius: 20px; padding: 6px 12px; font-size: 11px; font-weight: 600; color: #475569; display: inline-block;">
                        Secure 🛡️
                    </div>
                </td>
            </tr>
        </table>
        <div style="margin-bottom: 16px;">
            <div style="font-size: 12px; color: #64748b; font-weight: 500; margin-bottom: 4px;">ARCX Security &bull; Just now</div>
            <h3 style="margin: 0; font-size: 24px; font-weight: 700; color: #1e293b;">Reset Transaction PIN</h3>
        </div>
        <div style="margin-bottom: 24px;">
            <span style="background-color: #f1f5f9; border-radius: 20px; padding: 4px 12px; font-size: 11px; font-weight: 600; color: #475569; margin-right: 8px; display: inline-block;">Email OTP</span>
            <span style="background-color: #f1f5f9; border-radius: 20px; padding: 4px 12px; font-size: 11px; font-weight: 600; color: #475569; display: inline-block;">Valid 15m</span>
        </div>
        <div style="height: 1px; background-color: #f1f5f9; margin-bottom: 24px;"></div>
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="left" valign="middle">
                    <div style="font-size: 28px; font-weight: 800; color: #1e293b; letter-spacing: 2px;">{otp_code}</div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Do not share this code</div>
                </td>
            </tr>
        </table>
    </div>
</div>"""
        
        # Send Email
        try:
            send_mail(
                subject="ARCX - Your PIN Reset OTP",
                message=f"Your OTP to reset your transaction PIN is: {otp_code}\nThis OTP is valid for 15 minutes.",
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=[user.email],
                fail_silently=False,
                html_message=html_content
            )
            logger.info(f"OTP email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send OTP email to {user.email}: {e}")
            return Response({"error": "Failed to send email.", "code": "EMAIL_FAILED"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "OTP sent to your registered email."}, status=status.HTTP_200_OK)


class ResetPinView(APIView):
    """
    POST /api/v1/auth/reset-pin
    Validates the OTP and sets a new PIN.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Reset PIN (Validate OTP)",
        request=ResetPinRequestSerializer,
        responses={200: inline_serializer("ResetPinSuccess", {"message": drf_serializers.CharField()})}
    )
    def post(self, request):
        user_id = request.user.username
        try:
            from arcx_core.models import User
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found.", "code": "USER_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResetPinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        otp_record = OTPVerification.objects.filter(
            user=user,
            purpose="PIN_RESET",
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by("-created_at").first()
        
        if not otp_record or otp_record.code != data["otp"]:
            return Response({"error": "Invalid or expired OTP.", "code": "INVALID_OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
        otp_record.is_used = True
        otp_record.save()
        
        B2BService.set_transaction_pin(user, data["new_pin"])
        
        return Response({"message": "Transaction PIN has been reset successfully."}, status=status.HTTP_200_OK)