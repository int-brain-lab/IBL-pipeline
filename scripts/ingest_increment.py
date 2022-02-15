from ibl_pipeline.process import autoprocess, get_timezone, process_histology, process_qc, populate_wheel
import datetime
autoprocess.process_new(job_date=datetime.date.today().strftime('%Y-%m-%d'), timezone=get_timezone())
process_histology.main()
process_qc.main()
populate_wheel.main()
