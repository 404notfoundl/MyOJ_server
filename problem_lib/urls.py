from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'save', views.SaveProblems)
router.register(r'problems', views.GetProblems)
router.register(r'labels', views.ProblemsLabelView)
router.register(r'competition', views.CompetitionView)
router.register(r'competition_problems', views.CompetitionProblemView)
router.register(r'competition_rank', views.CompetitionRankView)
router.register(r'provincial_competition', views.provincial_competition.ProvincialCompetitionView)
router.register(r'spj', views.SpjProblems)

urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
