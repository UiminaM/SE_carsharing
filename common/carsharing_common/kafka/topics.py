
class Topics:
    CAR_EVENTS = "car.events"
    CAR_COMMANDS = "car.commands"
    CAR_LOCATION = "car.location"

    USER_EVENTS = "user.events"
    USER_COMMANDS = "user.commands"

    TRIP_EVENTS = "trip.events"
    TRIP_COMMANDS = "trip.commands"

    FLEET_LOCATION_STREAM = "fleet.location.stream"

    ARCHIVE_EVENTS = "archive.events"

    DLT_CAR_EVENTS = "car.events.dlt"
    DLT_USER_EVENTS = "user.events.dlt"
    DLT_TRIP_EVENTS = "trip.events.dlt"
    DLT_FLEET_LOCATION = "fleet.location.stream.dlt"

    @classmethod
    def all_topics(cls) -> list[str]:
        return [
            v for k, v in vars(cls).items()
            if isinstance(v, str) and not k.startswith("_")
        ]
