import datetime
import logging

from peewee import *


DB = SqliteDatabase('wizardtracker.db')
DB.connect()

# Hush, peewee.
peewee_logger = logging.getLogger('peewee')
peewee_logger.setLevel(logging.INFO)

class BaseModel(Model):
    class Meta:
        database = DB


class Race(BaseModel):
    name = CharField()
    created_on = DateTimeField(default=datetime.datetime.now)
    complete = BooleanField(default=False)


class RaceReceiver(BaseModel):
    receiver_id = IntegerField()
    frequency = IntegerField()
    race = ForeignKeyField(Race, backref='receivers')


class RaceRssi(BaseModel):
    timestamp = FloatField()
    receiver = ForeignKeyField(RaceReceiver, backref='rssi')
    value = IntegerField()
