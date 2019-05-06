'''
This script computes the latest event date happen to individual subject
and manually insert into the table behavior_plotting.LatestDate
'''

import datajoint as dj
from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.analyses import behavior as behavior_analyses
from ibl_pipeline.plotting import behavior as behavior_plotting
import numpy as np
from datetime import datetime


for key in subject.Subject():
    behavior_summary = behavior_analyses.BehavioralSummaryByDate & key
    water_weight = action.Weighing * action.WaterAdministration & key
    if behavior_summary:
        latest_behavior = (subject.Subject & key).aggr(
            behavior_analyses.BehavioralSummaryByDate,
            last_behavior_date='MAX(session_date)')

    if water_weight:
        latest_weight = (subject.Subject & key).aggr(
            action.Weighing,
            last_weighing_date='DATE(MAX(weighing_time))')
        latest_water = (subject.Subject & key).aggr(
            action.WaterAdministration,
            last_water_date='DATE(MAX(administration_time))')

        latest_water_weight = (latest_water * latest_weight).proj(
            last_water_weight_date='GREATEST(last_water_date, \
                                             last_weighing_date)'
        )

    if not(behavior_summary or water_weight):
        continue
    elif behavior_summary and water_weight:
        last_behavior_date = latest_behavior.fetch1(
            'last_behavior_date'
        )
        last_water_weight_date = water_weight.fetch1(
            'last_water_weight_date'
        )
        latest_date = max([last_behavior_date, last_water_weight_date])
    elif behavior_summary:
        latest_date = latest_behavior.fetch1(
            'last_behavior_date'
        )
    elif water_weight:
        latest_date = water_weight.fetch1(
            'last_water_weight_date'
        )

    key['latest_date'] = latest_date
    behavior_plotting.LatestDate.insert1(key)
