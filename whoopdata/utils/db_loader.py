from sqlalchemy.orm import Session
from whoopdata.models.models import (
    Recovery,
    Cycle,
    Sleep,
    Workout,
    WithingsWeight,
    WithingsHeartRate,
)


class DBLoader:
    """
    Helper class to insert WHOOP data into the database using SQLAlchemy ORM.
    This is essentially the `Load` in Extract Transform Load
    """

    def __init__(self, db: Session):
        """
        Initialize with an active SQLAlchemy database session.

        Args:
            db (Session): SQLAlchemy session object.
        """
        self.db = db

    def load_recovery(self, data: dict) -> Recovery:
        """
        Insert or update a Recovery record in the database (upsert).
        Uses cycle_id as the unique identifier to prevent duplicates.

        Args:
            data (dict): Dictionary of recovery data.

        Returns:
            Recovery: The created or updated Recovery ORM object.
        """
        # Check if record already exists (avoid duplicates)
        existing = (
            self.db.query(Recovery)
            .filter(
                Recovery.cycle_id == data.get("cycle_id"), Recovery.user_id == data.get("user_id")
            )
            .first()
        )

        if existing:
            # Update existing record
            for key, value in data.items():
                if value is not None:  # Only update non-None values
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new record
            recovery = Recovery(**data)
            self.db.add(recovery)
            self.db.commit()
            self.db.refresh(recovery)
            return recovery

    def load_cycle(self, data: dict) -> Cycle:
        """
        Insert a Cycle record into the database.

        Args:
            data (dict): Dictionary of cycle data.

        Returns:
            Cycle: The created Cycle ORM object.
        """
        cycle = Cycle(**data)
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    def load_workout(self, data: dict) -> Workout:
        """
        Insert or update a Workout record in the database (upsert).
        Uses whoop_id (WHOOP API string ID) as the unique identifier to prevent duplicates.

        Args:
            data (dict): Dictionary of workout data.

        Returns:
            Workout: The created or updated Workout ORM object.
        """
        # Check if record already exists (avoid duplicates) using whoop_id
        existing = None
        if data.get("whoop_id"):
            existing = (
                self.db.query(Workout)
                .filter(Workout.whoop_id == data.get("whoop_id"))
                .first()
            )

        if existing:
            # Update existing record
            for key, value in data.items():
                if value is not None:  # Only update non-None values
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new record
            workout = Workout(**data)
            self.db.add(workout)
            self.db.commit()
            self.db.refresh(workout)
            return workout

    def load_sleep(self, data: dict) -> Sleep:
        """
        Insert or update a Sleep record in the database (upsert).
        Uses whoop_id (WHOOP API string ID) as the unique identifier to prevent duplicates.

        Args:
            data (dict): Dictionary of sleep data.

        Returns:
            Sleep: The created or updated Sleep ORM object.
        """
        # Check if record already exists (avoid duplicates) using whoop_id
        existing = None
        if data.get("whoop_id"):
            existing = (
                self.db.query(Sleep)
                .filter(Sleep.whoop_id == data.get("whoop_id"))
                .first()
            )

        if existing:
            # Update existing record
            for key, value in data.items():
                if value is not None:  # Only update non-None values
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new record
            sleep = Sleep(**data)
            self.db.add(sleep)
            self.db.commit()
            self.db.refresh(sleep)
            return sleep

    def load_withings_weight(self, data: dict) -> WithingsWeight:
        """
        Insert a Withings Weight record into the database.

        Args:
            data (dict): Dictionary of Withings weight/body composition data.

        Returns:
            WithingsWeight: The created WithingsWeight ORM object.
        """
        # Check if record already exists (avoid duplicates)
        existing = (
            self.db.query(WithingsWeight)
            .filter(
                WithingsWeight.grpid == data.get("grpid"),
                WithingsWeight.user_id == data.get("user_id"),
            )
            .first()
        )

        if existing:
            # Update existing record
            for key, value in data.items():
                if value is not None:  # Only update non-None values
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new record
            weight_record = WithingsWeight(**data)
            self.db.add(weight_record)
            self.db.commit()
            self.db.refresh(weight_record)
            return weight_record

    def load_withings_heart_rate(self, data: dict) -> WithingsHeartRate:
        """
        Insert a Withings Heart Rate record into the database.

        Args:
            data (dict): Dictionary of Withings heart rate/blood pressure data.

        Returns:
            WithingsHeartRate: The created WithingsHeartRate ORM object.
        """
        # Check if record already exists (avoid duplicates)
        existing = (
            self.db.query(WithingsHeartRate)
            .filter(
                WithingsHeartRate.grpid == data.get("grpid"),
                WithingsHeartRate.user_id == data.get("user_id"),
            )
            .first()
        )

        if existing:
            # Update existing record
            for key, value in data.items():
                if value is not None:  # Only update non-None values
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new record
            hr_record = WithingsHeartRate(**data)
            self.db.add(hr_record)
            self.db.commit()
            self.db.refresh(hr_record)
            return hr_record
