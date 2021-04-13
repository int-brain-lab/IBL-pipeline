from ibl_pipeline.process import autoprocess, get_timezone, process_histology, process_qc, process_wheel

autoprocess.process_new(timezone=get_timezone())
process_histology.main()
process_qc.main()
process_wheel.main()
