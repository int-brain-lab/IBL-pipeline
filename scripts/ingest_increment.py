from ibl_pipeline.process import autoprocess, get_timezone, process_histology, process_qc, populate_wheel

autoprocess.process_new(timezone=get_timezone())
process_histology.main()
process_qc.main()
populate_wheel.main()
