import logging
import datetime
import pathlib
import time

from ibl_pipeline.group_shared import wheel
from ibl_pipeline import mode, ephys

log_path = pathlib.Path(__file__).parent / 'logs'
log_path.mkdir(parents=True, exist_ok=True)
log_file = log_path / f'process_wheel{"_public" if mode == "public" else ""}.log'
log_file.touch(exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()],
    level=25)

logger = logging.getLogger(__name__)

gkwargs = dict(display_progress=True, suppress_errors=True)


def main(backtrack_days=30, run_duration=3600*3, sleep_duration=60, **kwargs):
    start_time = time.time()
    while ((time.time() - start_time < run_duration)
           or (run_duration is None)
           or (run_duration < 0)):

        date_cutoff = \
            (datetime.datetime.now().date() -
            datetime.timedelta(days=backtrack_days)).strftime('%Y-%m-%d')
        date_range = f'session_start_time > "{date_cutoff}"'

        logger.log(25, 'Populating WheelMoveSet...')
        wheel.WheelMoveSet.populate(date_range, ephys.ProbeInsertion, **gkwargs)

        logger.log(25, 'Populating MovementTimes...')
        wheel.MovementTimes.populate(date_range, ephys.ProbeInsertion, **gkwargs)

        time.sleep(sleep_duration)


if __name__ == '__main__':
    main()
