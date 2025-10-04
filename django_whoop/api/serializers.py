from rest_framework import serializers
from .models import Recovery, Cycle, Sleep, Workout

class CycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cycle
        fields = '__all__'

class SleepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sleep
        fields = '__all__'

class WorkoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workout
        fields = '__all__'

class RecoverySerializer(serializers.ModelSerializer):
    cycle = CycleSerializer(read_only=True)
    sleep = SleepSerializer(read_only=True)

    class Meta:
        model = Recovery
        fields = '__all__'

class AvgRecoverySerializer(serializers.Serializer):
    week = serializers.IntegerField()
    avg_recovery_score = serializers.FloatField()
    avg_resting_heart_rate = serializers.FloatField()
