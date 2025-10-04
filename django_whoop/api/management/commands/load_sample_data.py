import datetime
from django.core.management.base import BaseCommand
from api.models import Cycle, Sleep, Recovery, Workout

class Command(BaseCommand):
    help = 'Loads sample data into the database'

    def handle(self, *args, **options):
        self.stdout.write('Loading sample data...')

        # Create a cycle
        cycle1 = Cycle.objects.create(
            user_id='test_user',
            start=datetime.datetime.now() - datetime.timedelta(days=1),
            end=datetime.datetime.now(),
            strain=10.5,
            kilojoule=2000,
            average_heart_rate=60,
            max_heart_rate=120,
        )

        # Create a sleep
        sleep1 = Sleep.objects.create(
            user_id='test_user',
            start=datetime.datetime.now() - datetime.timedelta(hours=8),
            end=datetime.datetime.now(),
            respiratory_rate=15.2,
            sleep_performance_percentage=85.0,
        )

        # Create a recovery
        Recovery.objects.create(
            user_id='test_user',
            cycle=cycle1,
            sleep=sleep1,
            recovery_score=75.0,
            resting_heart_rate=55.0,
            hrv_rmssd_milli=45.0,
            spo2_percentage=98.0,
            skin_temp_celsius=36.5,
        )

        # Create a run
        Workout.objects.create(
            user_id='test_user',
            cycle=cycle1,
            sport_id=0,
            start=datetime.datetime.now() - datetime.timedelta(hours=2),
            end=datetime.datetime.now() - datetime.timedelta(hours=1),
            strain=12.0,
            average_heart_rate=140,
            max_heart_rate=180,
            kilojoule=500,
            distance_meter=5000,
            zone_zero_minutes=10,
            zone_one_minutes=20,
            zone_two_minutes=15,
            zone_three_minutes=10,
            zone_four_minutes=5,
            zone_five_minutes=0,
        )

        # Create a tennis match
        Workout.objects.create(
            user_id='test_user',
            cycle=cycle1,
            sport_id=34,
            start=datetime.datetime.now() - datetime.timedelta(days=2, hours=2),
            end=datetime.datetime.now() - datetime.timedelta(days=2, hours=1),
            strain=8.0,
            average_heart_rate=130,
            max_heart_rate=170,
            kilojoule=400,
        )

        self.stdout.write(self.style.SUCCESS('Successfully loaded sample data.'))
