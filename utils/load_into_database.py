from sqlalchemy.orm import Session
from models.models import Recovery, Cycle, Sleep, Workout

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
        Insert a Recovery record into the database.

        Args:
            data (dict): Dictionary of recovery data.

        Returns:
            Recovery: The created Recovery ORM object.
        """
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
        Insert a Workout record into the database.

        Args:
            data (dict): Dictionary of workout data.

        Returns:
            Workout: The created Workout ORM object.
        """
        workout = Workout(**data)
        self.db.add(workout)
        self.db.commit()
        self.db.refresh(workout)
        return workout

    def load_sleep(self, data: dict) -> Sleep:
        """
        Insert a Sleep record into the database.

        Args:
            data (dict): Dictionary of sleep data.

        Returns:
            Sleep: The created Sleep ORM object.
        """
        sleep = Sleep(**data)
        self.db.add(sleep)
        self.db.commit()
        self.db.refresh(sleep)
        return sleep
