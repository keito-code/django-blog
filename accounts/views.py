from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken  # ← ここでimport
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    PublicUserSerializer,      
    PrivateUserSerializer,      
    AdminUserSerializer,        
    UserSerializer
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                {'detail': 'ユーザー名またはパスワードが正しくありません'},
                status=status.HTTP_401_UNAUTHORIZED
            )

         # ユーザーオブジェクトを直接取得してチェック
        username = request.data.get('username')
        try:
            user = User.objects.get(username=username)
            if user.is_staff or user.is_superuser:
                return Response(
                    {'detail': '管理者アカウントではブログシステムにログインできません'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except User.DoesNotExist:
            pass  # ユーザーが見つからない場合は通常のエラーで処理
        
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
        
        
class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer  # ← drf-spectacularの警告対策

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # 管理者アカウントの登録を防ぐ
            if user.is_staff or user.is_superuser:
                user.delete()
                return Response(
                    {'detail': '管理者アカウントは登録できません'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': PublicUserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None  # ← ログアウトにはシリアライザー不要と明示

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response(
                    {'detail': 'ログアウトしました'},
                    status=status.HTTP_200_OK
                )
            return Response(
                {'detail': 'Refresh tokenが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except TokenError:
            return Response(
                {'detail': '無効なトークンです'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PrivateUserSerializer

    def get(self, request):
        # 自分の情報なのでPrivateUserSerializerを使用
        if request.user.is_staff:
            serializer = AdminUserSerializer(request.user)
        else:
            serializer = PrivateUserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        # 更新時もPrivateUserSerializerを使用
        if request.user.is_staff:
            serializer = AdminUserSerializer(request.user, data=request.data, partial=True)
        else:
            serializer = PrivateUserSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'token': {'type': 'string', 'description': 'JWTアクセストークン'}
            },
            'required': ['token']
        }
    },
    responses={
        200: OpenApiResponse(
            description="トークンは有効です",
            response={
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'user': {'type': 'object', 'description': 'ユーザー情報（オプション）'}
                }
            }
        ),
        400: OpenApiResponse(description="トークンが必要です"),
        401: OpenApiResponse(description="トークンが無効です"),
        403: OpenApiResponse(description="管理者トークンは無効です")
    },
    summary="トークン検証",
    description="JWTアクセストークンの有効性を検証します",
    
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_token(request):
    """トークンの有効性を確認"""
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'valid': False, 'detail': 'トークンが必要です'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        access_token = AccessToken(token)
        
        # トークンからユーザー情報を取得（オプション）
        user_id = access_token.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                # 管理者チェック
                if user.is_staff or user.is_superuser:
                    return Response(
                        {'valid': False, 'detail': '管理者トークンは無効です'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                return Response({
                    'valid': True,
                    'user': PublicUserSerializer(user).data
                }, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                pass
        
        return Response({'valid': True}, status=status.HTTP_200_OK)
        
    except TokenError as e:
        return Response(
            {'valid': False, 'detail': str(e)},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'valid': False, 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )