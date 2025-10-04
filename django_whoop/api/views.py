from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Recovery, Workout
from .serializers import RecoverySerializer, AvgRecoverySerializer, WorkoutSerializer
from django.db.models import Avg
from django.db.models.functions import TruncWeek

class RecoveryListView(generics.ListAPIView):
    queryset = Recovery.objects.all()
    serializer_class = RecoverySerializer

class TopRecoveriesView(generics.ListAPIView):
    serializer_class = RecoverySerializer

    def get_queryset(self):
        limit = self.request.query_params.get('limit', 10)
        return Recovery.objects.order_by('-recovery_score')[:int(limit)]

class AvgRecoveryByWeekView(APIView):
    def get(self, request):
        weeks = int(request.query_params.get('weeks', 4))
        avg_recoveries = Recovery.objects.annotate(week=TruncWeek('created_at')).values('week').annotate(
            avg_recovery_score=Avg('recovery_score'),
            avg_resting_heart_rate=Avg('resting_heart_rate')
        ).order_by('-week')[:weeks]

        serializer = AvgRecoverySerializer(avg_recoveries, many=True)
        return Response(serializer.data)

class WorkoutListView(generics.ListCreateAPIView):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        sport_id = self.request.query_params.get('sport_id')
        if sport_id:
            queryset = queryset.filter(sport_id=sport_id)
        return queryset

    def perform_create(self, serializer):
        instance_data = serializer.validated_data
        instance, created = Workout.objects.update_or_create(
            id=instance_data.get('id'),
            defaults=instance_data
        )
        return instance

class RunListView(generics.ListAPIView):
    serializer_class = WorkoutSerializer

    def get_queryset(self):
        return Workout.objects.filter(sport_id=0).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        for run in data:
            run['trimp_score'] = self.calculate_trimp_from_run(run)
        return Response(data)

    def calculate_trimp_from_run(self, run) -> float:
        weights = {0: 0.5, 1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 5.0}
        time_in_zones = {
            0: run.get('zone_zero_minutes', 0),
            1: run.get('zone_one_minutes', 0),
            2: run.get('zone_two_minutes', 0),
            3: run.get('zone_three_minutes', 0),
            4: run.get('zone_four_minutes', 0),
            5: run.get('zone_five_minutes', 0),
        }
        trimp = round(sum(minutes * weights[zone] for zone, minutes in time_in_zones.items() if minutes), 2)
        return trimp

class TennisListView(generics.ListAPIView):
    serializer_class = WorkoutSerializer
    
    def get_queryset(self):
        return Workout.objects.filter(sport_id=34).order_by('-created_at')
