import datetime
import time

from ibl_pipeline import ephys
from ibl_pipeline.group_shared import wheel
from ibl_pipeline.utils import get_logger

logger = get_logger(__name__)


def main(
    backtrack_days=30,
    run_duration=3600 * 3,
    sleep_duration=60,
    populate_settings=None,
    **kwargs,
):
    populate_settings = (populate_settings or {}) | {
        "display_progress": True,
        "reserve_jobs": True,
        "suppress_errors": True,
    }

    start_time = time.time()
    while (
        (time.time() - start_time < run_duration)
        or (run_duration is None)
        or (run_duration < 0)
    ):

        date_cutoff = (
            datetime.datetime.now().date() - datetime.timedelta(days=backtrack_days)
        ).strftime("%Y-%m-%d")
        date_range = f'session_start_time > "{date_cutoff}"'

        logger.info("Populating WheelMoveSet...")
        wheel.WheelMoveSet.populate(
            date_range, ephys.ProbeInsertion, **populate_settings
        )

        logger.info("Populating MovementTimes...")
        wheel.MovementTimes.populate(
            date_range, ephys.ProbeInsertion, **populate_settings
        )

        time.sleep(sleep_duration)


if __name__ == "__main__":
    main()
