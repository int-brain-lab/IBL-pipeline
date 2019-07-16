import datajoint as dj
from .. import behavior, ephys
from . import plotting_utils as putils
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import json

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_plotting_ephys')


@schema
class Sorting(dj.Lookup):
    definition = """
    sort_by:     varchar(32)
    """
    contents = zip(['trial_id',
                    'response - stim on',
                    'feedback - stim on',
                    'feedback - response'])


@schema
class ValidAlignSort(dj.Lookup):
    definition = """
    -> ephys.Event
    -> Sorting
    """
    contents = [
        ['stim on', 'trial_id'],
        ['stim on', 'response - stim on'],
        ['stim on', 'feedback - stim on'],
        ['response', 'trial_id'],
        ['response', 'response - stim on'],
        ['response', 'feedback - response'],
        ['feedback', 'trial_id'],
        ['feedback', 'feedback - stim on'],
        ['feedback', 'feedback - response']
    ]


@schema
class TrialCondition(dj.Lookup):
    definition = """
    trial_condition:  varchar(32)
    """

    contents = zip(['all trials',
                    'correct trials',
                    'left trials',
                    'right trials'])


@schema
class Raster(dj.Computed):
    definition = """
    -> ephys.Cluster
    -> ValidAlignSort
    -> TrialCondition
    ---
    plotting_data:      longblob
    """

    def make(self, key):
        cluster = ephys.Cluster & key
        trials_all = \
            (behavior.TrialSet.Trial * ephys.TrialSpikes & cluster).proj(
                'trial_start_time', 'trial_stim_on_time',
                'trial_response_time',
                'trial_feedback_time',
                'trial_response_choice',
                'trial_spike_times',
                trial_duration='trial_end_time-trial_start_time',
                trial_signed_contrast="""trial_stim_contrast_right -
                                         trial_stim_contrast_left"""
            ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"'

        trial_condition = (TrialCondition & key).fetch1('trial_condition')

        if trial_condition == 'all trials':
            trials = trials_all
        else:
            trials_left = trials_all & 'trial_response_choice="CW"' & \
                'trial_signed_contrast < 0'
            trials_right = trials_all & 'trial_response_choice="CCW"' & \
                'trial_signed_contrast > 0'
            if trial_condition == 'correct trials':
                trials = trials_all & [trials_left.proj(), trials_right.proj()]
            elif trial_condition == 'left trials':
                trials = trials_left
            elif trial_condition == 'right trials':
                trials = trials_right
            else:
                raise NameError(
                    'Unknown trial condition {}'.format(trial_condition))

        if not len(trials):
            return
        align_event = (ephys.Event & key).fetch1('event')
        sorting_var = (Sorting & key).fetch1('sort_by')
        x_lim = [-1, 1]
        encoded_string, y_lim = putils.create_raster_plot(
            trials, align_event, sorting_var)

        data = go.Scatter(
            x=x_lim,
            y=y_lim,
            mode='markers',
            marker=dict(opacity=0)
        )

        layout = go.Layout(
            images=[dict(
                source='data:image/png;base64, ' + encoded_string.decode(),
                sizex=x_lim[1] - x_lim[0],
                sizey=y_lim[1] - y_lim[0],
                x=x_lim[0],
                y=y_lim[1],
                xref='x',
                yref='y',
                sizing='stretch',
                layer='below'
            )],
            width=580,
            height=370,
            margin=go.layout.Margin(
                l=50,
                r=30,
                b=40,
                t=80,
                pad=0
            ),
            title=dict(
                text='Raster, aligned to {}'.format(align_event),
                y=0.87
            ),
            xaxis=dict(
                title='Time/sec',
                range=x_lim,
                showgrid=False
            ),
            yaxis=dict(
                title='Trial idx',
                range=y_lim,
                showgrid=False
            ),
        )

        fig = go.Figure(data=[data], layout=layout)
        key['plotting_data'] = fig.to_plotly_json()
        self.insert1(key)
