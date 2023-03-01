from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('submit', views.PreJudgeView, basename='submit_task')
router.register('preview', views.AfterJudgeView, basename='preview_task')
router.register('competition', views.CompetitionJudgeView, basename='competition_task')

urlpatterns = [
    path('', include(router.urls))
]
