from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView
)

router = DefaultRouter()
router.register('info', views.UserView)
router.register('details', views.UserDetailsView, basename="details")

app_name = 'loginApi'

urlpatterns = [
    path('login/', views.UserLoginView.as_view()),
    path('refresh/', TokenRefreshView.as_view()),
    path('verify/', TokenVerifyView.as_view()),
    path('register/', views.UserRegister.as_view()),
    path('', include(router.urls))
]
