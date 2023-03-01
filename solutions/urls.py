from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('submit', views.ProblemSolutionView, basename='submit')
router.register('preview', views.PreviewProblemSolutionView, basename='preview')
router.register('check', views.SolutionBufferView)
urlpatterns = [
    path('', include(router.urls))
]
