from ibl_pipeline.process import autoprocess, get_timezone, process_histology

autoprocess.process_new(timezone=get_timezone())
process_histology.main()
