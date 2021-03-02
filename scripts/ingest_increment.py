from ibl_pipeline.process import autoprocess, get_timezone, process_histology, process_qc
from ibl_pipeline.group_shared import wheel

autoprocess.process_new(timezone=get_timezone())
process_histology.main()
process_qc.main()
wheel.WheelMoveSet.populate(display_progress=True, suppress_errors=True)
wheel.MovementTimes.populate(display_progress=True, suppress_errors=True)
