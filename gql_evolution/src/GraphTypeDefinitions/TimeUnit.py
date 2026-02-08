import enum
import strawberry

@strawberry.enum(description="Time unit enum for duration and aggregation windows")
class TimeUnit(enum.Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"