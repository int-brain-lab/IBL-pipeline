import sys

from ibl_pipeline.ingest import job
from ibl_pipeline.process import populate_behavior, populate_ephys, populate_wheel

if __name__ == "__main__":
    if sys.argv[1] == "ingest":
        job.populate_ingestion_tables(run_duration=-1)
    elif sys.argv[1] == "behavior":
        populate_behavior.main(backtrack_days=3, run_duration=-1)
    elif sys.argv[1] == "wheel":
        populate_wheel.main(backtrack_days=3, run_duration=-1)
    elif sys.argv[1] == "ephys":
        populate_ephys.main(run_duration=-1)
    else:
        raise ValueError(
            f"Usage error! Unknown argument {sys.argv[1]}. "
            f"Accepting: ingest|behavior|wheel|ephys"
        )
