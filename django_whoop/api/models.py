from django.db import models

class Cycle(models.Model):
    user_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    timezone_offset = models.CharField(max_length=50, blank=True, null=True)
    score_state = models.CharField(max_length=50, blank=True, null=True)
    strain = models.FloatField(blank=True, null=True)
    kilojoule = models.FloatField(blank=True, null=True)
    average_heart_rate = models.FloatField(blank=True, null=True)
    max_heart_rate = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Cycle {self.id} for user {self.user_id}"

class Sleep(models.Model):
    user_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    timezone_offset = models.CharField(max_length=50, blank=True, null=True)
    nap = models.BooleanField(default=False)
    score_state = models.CharField(max_length=50, blank=True, null=True)
    respiratory_rate = models.FloatField(blank=True, null=True)
    sleep_performance_percentage = models.FloatField(blank=True, null=True)
    sleep_consistency_percentage = models.FloatField(blank=True, null=True)
    sleep_efficiency_percentage = models.FloatField(blank=True, null=True)
    total_time_in_bed_time_milli = models.IntegerField(blank=True, null=True)
    total_awake_time_milli = models.IntegerField(blank=True, null=True)
    total_no_data_time_milli = models.IntegerField(blank=True, null=True)
    total_slow_wave_sleep_time_milli = models.IntegerField(blank=True, null=True)
    total_rem_sleep_time_milli = models.IntegerField(blank=True, null=True)
    sleep_cycle_count = models.IntegerField(blank=True, null=True)
    disturbance_count = models.IntegerField(blank=True, null=True)
    baseline_sleep_needed_milli = models.IntegerField(blank=True, null=True)
    need_from_sleep_debt_milli = models.IntegerField(blank=True, null=True)
    need_from_recent_strain_milli = models.IntegerField(blank=True, null=True)
    need_from_recent_nap_milli = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Sleep {self.id} for user {self.user_id}"

class Recovery(models.Model):
    user_id = models.CharField(max_length=255)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='recoveries')
    sleep = models.ForeignKey(Sleep, on_delete=models.CASCADE, related_name='recoveries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    score_state = models.CharField(max_length=50, blank=True, null=True)
    user_calibrating = models.BooleanField(default=False)
    recovery_score = models.FloatField(blank=True, null=True)
    resting_heart_rate = models.FloatField(blank=True, null=True)
    hrv_rmssd_milli = models.FloatField(blank=True, null=True)
    spo2_percentage = models.FloatField(blank=True, null=True)
    skin_temp_celsius = models.FloatField(blank=True, null=True)

    def recovery_category(self):
        if self.recovery_score >= 67:
            return 'Green'
        elif 34 <= self.recovery_score < 67:
            return 'Yellow'
        else:
            return 'Red'

    def is_weekend(self) -> bool:
        if self.created_at:
            return self.created_at.weekday() > 4  # 5 = Saturday, 6 = Sunday
        return False

    def __str__(self):
        return f"Recovery {self.id} for user {self.user_id}"

class Workout(models.Model):
    user_id = models.CharField(max_length=255)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='workouts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    timezone_offset = models.CharField(max_length=50, blank=True, null=True)
    sport_id = models.IntegerField(blank=True, null=True)
    score_state = models.CharField(max_length=50, blank=True, null=True)
    strain = models.FloatField(blank=True, null=True)
    average_heart_rate = models.FloatField(blank=True, null=True)
    max_heart_rate = models.FloatField(blank=True, null=True)
    kilojoule = models.FloatField(blank=True, null=True)
    percent_recorded = models.FloatField(blank=True, null=True)
    distance_meter = models.FloatField(blank=True, null=True)
    altitude_gain_meter = models.FloatField(blank=True, null=True)
    altitude_change_meter = models.FloatField(blank=True, null=True)
    zone_zero_minutes = models.FloatField(blank=True, null=True)
    zone_one_minutes = models.FloatField(blank=True, null=True)
    zone_two_minutes = models.FloatField(blank=True, null=True)
    zone_three_minutes = models.FloatField(blank=True, null=True)
    zone_four_minutes = models.FloatField(blank=True, null=True)
    zone_five_minutes = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Workout {self.id} for user {self.user_id}"