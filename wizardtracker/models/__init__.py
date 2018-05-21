import datetime
import logging

from peewee import *


DB = SqliteDatabase('wizardtracker.db', pragmas=(('foreign_keys', 'on'),))
DB.connect()

# Hush, peewee.
PEEWEE_LOGGER = logging.getLogger('peewee')
PEEWEE_LOGGER.setLevel(logging.INFO)


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
    race = ForeignKeyField(Race, backref='receivers', on_delete='cascade')


class RaceRssi(BaseModel):
    timestamp = FloatField()
    receiver = ForeignKeyField(
        RaceReceiver,
        backref='rssi',
        on_delete='cascade')
    value = IntegerField()
