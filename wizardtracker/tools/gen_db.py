from wizardtracker.models import (
    DB,
    Race,
    RaceReceiver,
    RaceRssi
)


DB.create_tables([Race, RaceReceiver, RaceRssi])
