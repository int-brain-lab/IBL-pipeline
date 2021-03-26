from ibl_pipeline.group_shared import wheel
import logging
import datetime

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("/src/IBL-pipeline/ibl_pipeline/process/logs/process_wheel.log"),
        logging.StreamHandler()],
    level=25)

logger = logging.getLogger(__name__)

def main(backtrack_days=30):

    date_cutoff = \
        (datetime.datetime.now().date() -
        datetime.timedelta(days=backtrack_days)).strftime('%Y-%m-%d')
    date_range = f'session_start_time > "{date_cutoff}"'

    kwargs = dict(display_progress=True, suppress_errors=True)
    logger.log(25, 'Populating WheelMoveSet...')
    wheel.WheelMoveSet.populate(date_range, **kwargs)

    logger.log(25, 'Populating MovementTimes...')
    wheel.MovementTimes.populate(date_range, **kwargs)


if __name__ == '__main__':
    main()
