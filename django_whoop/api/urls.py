from django.urls import path
from .views import (
    RecoveryListView, 
    TopRecoveriesView, 
    AvgRecoveryByWeekView,
    WorkoutListView,
    RunListView,
    TennisListView
)

urlpatterns = [
    path('recoveries/', RecoveryListView.as_view(), name='recovery-list'),
    path('recoveries/top/', TopRecoveriesView.as_view(), name='top-recoveries'),
    path('recoveries/avg_recoveries/', AvgRecoveryByWeekView.as_view(), name='avg-recovery-by-week'),
    path('workouts/', WorkoutListView.as_view(), name='workout-list'),
    path('workouts/runs/', RunListView.as_view(), name='run-list'),
    path('workouts/tennis/', TennisListView.as_view(), name='tennis-list'),
]