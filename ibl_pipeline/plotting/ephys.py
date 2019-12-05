import datajoint as dj
from .. import behavior, ephys
from . import plotting_utils_ephys as putils
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import json
from os import path

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
    ---
    plotting_data:      blob@plotting
    """
    key_source = ephys.Cluster * ValidAlignSort & behavior.TrialSet & ephys.TrialSpikes

    def make(self, key):
        cluster = ephys.Cluster & key
        trials = \
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

        if not len(trials):
            return
        align_event = (ephys.Event & key).fetch1('event')
        sorting_var = (Sorting & key).fetch1('sort_by')
        x_lim = [-1, 1]
        encoded_string, y_lim, label = putils.create_raster_plot_combined(
            trials, align_event, sorting_var)

        axis = go.Scatter(
            x=x_lim,
            y=y_lim,
            mode='markers',
            marker=dict(opacity=0),
            showlegend=False
        )

        legend_left = putils.get_legend('left', 'spike')
        legend_right = putils.get_legend('right', 'spike')
        legend_incorrect = putils.get_legend('incorrect', 'spike')

        if sorting_var != 'trial_id':
            legend_mark_left = putils.get_legend('left', label)
            legend_mark_right = putils.get_legend('right', label)
            legend_mark_incorrect = putils.get_legend('incorrect', label)

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
                x=0.21,
                y=0.87
            ),
            xaxis=dict(
                title='Time (sec)',
                range=x_lim,
                showgrid=False
            ),
            yaxis=dict(
                title='Trial idx',
                range=y_lim,
                showgrid=False
            ),
        #     template=dict(
        #         layout=dict(
        #             plot_bgcolor="#fff"
        #         )
        #     )
        )

        if sorting_var != 'trial_id':
            data = [axis, legend_left, legend_right, legend_incorrect,
                    legend_mark_left, legend_mark_right, legend_mark_incorrect]
        else:
            data = [axis, legend_left, legend_right, legend_incorrect]

        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()

        self.insert1(key)


@schema
class RasterLayoutTemplate(dj.Lookup):
    definition = """
    template_idx:   int
    ---
    raster_data_template:   longblob
    """

    axis = go.Scatter(
        x=[-1, 1],
        # y=y_lim,
        mode='markers',
        marker=dict(opacity=0),
        showlegend=False
    )
    legend_left = putils.get_legend('left', 'spike')
    legend_right = putils.get_legend('right', 'spike')
    legend_incorrect = putils.get_legend('incorrect', 'spike')

    legend_mark_left = putils.get_legend('left', 'event')
    legend_mark_right = putils.get_legend('right', 'event')
    legend_mark_incorrect = putils.get_legend('incorrect', 'event')

    layout = go.Layout(
        images=[dict(
            source='',
            sizex=2,
            #sizey=y_lim[1] - y_lim[0],
            x=-1,
            #y=y_lim[1],
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
            text='Raster, aligned to ', # add align_event here
            x=0.21,
            y=0.87
        ),
        xaxis=dict(
            title='Time (sec)',
            range=[-1, 1],
            showgrid=False
        ),
        yaxis=dict(
            title='Trial idx',
            showgrid=False
        ),
    )
    data1 = [axis, legend_left, legend_right, legend_incorrect]
    data2 = [axis, legend_left, legend_right, legend_incorrect,
             legend_mark_left, legend_mark_right, legend_mark_incorrect]

    template_1 = dict(
        template_idx=0,
        raster_data_template=go.Figure(data=data1, layout=layout).to_plotly_json()
    )
    template_2 = dict(
        template_idx=1,
        raster_data_template=go.Figure(data=data2, layout=layout).to_plotly_json()
    )

    contents = [
        template_1,
        template_2
    ]


@schema
class RasterLinkS3(dj.Computed):
    definition = """
    -> ephys.Cluster
    -> ValidAlignSort
    ---
    plotting_data_link=null: varchar(255)
    plot_ylim:               blob
    mark_label=null:         varchar(32)
    -> RasterLayoutTemplate
    """
    key_source = ephys.Cluster * ValidAlignSort & behavior.TrialSet & ephys.TrialSpikes

    def make(self, key):
        cluster = ephys.Cluster & key
        trials = \
            (behavior.TrialSet.Trial * ephys.TrialSpikes & cluster).proj(
                'trial_start_time', 'trial_stim_on_time',
                'trial_response_time',
                'trial_feedback_time',
                'trial_response_choice',
                'trial_spike_times',
                trial_duration='trial_end_time-trial_start_time',
                trial_signed_contrast="""trial_stim_contrast_right -
                                         trial_stim_contrast_left"""
            ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"' & key

        if not len(trials):
            if key['sort_by'] == 'trial_id':
                key['template_idx'] = 0
            else:
                key['template_idx'] = 1
            self.insert1(dict(
                **key, plot_ylim=[0, 3]))
            return

        align_event = (ephys.Event & key).fetch1('event')
        sorting_var = (Sorting & key).fetch1('sort_by')

        fig_link = path.join('raster',
                             str(key['subject_uuid']),
                             key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
                             str(key['probe_idx']),
                             str(key['cluster_revision']),
                             key['event'],
                             key['sort_by'],
                             str(key['cluster_id'])) + '.png'
        y_lim, label = putils.create_raster_plot_combined(
            trials, align_event, sorting_var, fig_dir=fig_link, store_type='s3')
        key['plotting_data_link'] = fig_link
        key['plot_ylim'] = y_lim
        key['mark_label'] = label

        if key['sort_by'] == 'trial_id':
            key['template_idx'] = 0
        else:
            key['template_idx'] = 1

        self.insert1(key)


@schema
class Psth(dj.Computed):
    definition = """
    -> ephys.Cluster
    -> ephys.Event
    ---
    plotting_data:     blob@plotting
    """

    key_source = ephys.Cluster * (ephys.Event & 'event != "go cue"') & \
        behavior.TrialSet & ephys.TrialSpikes

    def make(self, key):
        cluster = ephys.Cluster & key
        trials_all = (behavior.TrialSet.Trial * ephys.TrialSpikes & cluster).proj(
            'trial_start_time', 'trial_stim_on_time',
            'trial_response_time', 'trial_feedback_time',
            'trial_response_choice', 'trial_spike_times',
            trial_duration='trial_end_time-trial_start_time',
            trial_signed_contrast='trial_stim_contrast_right - trial_stim_contrast_left'
        ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"' & key

        trials_left = trials_all & 'trial_response_choice="CW"' \
            & 'trial_signed_contrast < 0'
        trials_right = trials_all & 'trial_response_choice="CCW"' \
            & 'trial_signed_contrast > 0'
        trials_incorrect = trials_all - \
            trials_right.proj() - trials_left.proj()

        align_event = (ephys.Event & key).fetch1('event')
        x_lim = [-1, 1]
        data = []
        if len(trials_left):
            data.append(
                putils.compute_psth(trials_left, 'left', align_event))
        if len(trials_right):
            data.append(
                putils.compute_psth(trials_right, 'right', align_event))
        if len(trials_incorrect):
            data.append(
                putils.compute_psth(trials_incorrect, 'incorrect', align_event))

        data.append(
            putils.compute_psth(
                trials_all, 'all', align_event))

        layout = dict(
            width=580,
            height=370,
            margin=dict(
                l=50,
                r=30,
                b=40,
                t=80,
                pad=0
            ),
            title=dict(
                text='PSTH, aligned to {} time'.format(align_event),
                x=0.2,
                y=0.87
            ),
            xaxis=dict(
                title='Time (sec)',
                range=x_lim,
                showgrid=False
            ),
            yaxis=dict(
                title='Firing rate (spks/sec)',
                showgrid=False
            ),
        )

        fig = go.Figure(data=data, layout=layout)
        key['plotting_data'] = fig.to_plotly_json()

        self.insert1(key)


@schema
class PsthTemplate(dj.Lookup):
    definition = """
    psth_template_idx:   int
    ---
    psth_data_template:  longblob
    """

    left = go.Scatter(
        # x=psth_time, # fetched from the table PsthData
        # y=psth_left, # fetched from the table PsthData
        mode='lines',
        marker=dict(
            size=6,
            color='green'),
        name='left trials'
    )
    right = go.Scatter(
        # x=psth_time, # fetched from the table PsthData
        # y=psth_right, # fetched from the table PsthData
        mode='lines',
        marker=dict(
            size=6,
            color='blue'),
        name='right trials'
    )
    incorrect = go.Scatter(
        # x=psth_time, # fetched from the table PsthData
        # y=psth_incorrect, # fetched from the table PsthData
        mode='lines',
        marker=dict(
            size=6,
            color='red'),
        name='incorrect trials'
    )
    all = go.Scatter(
        # x=psth_time, # fetched from the table PsthData
        # y=psth_all, # fetched from the table PsthData
        mode='lines',
        marker=dict(
            size=6,
            color='black'),
        name='all trials'
    )

    layout = go.Layout(
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
            # text='PSTH, aligned to {} time'.format(align_event),  # to be inserted
            x=0.2,
            y=0.87
        ),
        xaxis=dict(
            title='Time (sec)',
            # range=psth_x_lim,  # to be filled, fetch from PsthData
            showgrid=False
        ),
        yaxis=dict(
            title='Firing rate (spks/sec)',
            showgrid=False
        ),
    )

    contents = [dict(
        psth_template_idx=0,
        psth_data_template=go.Figure(data=[left, right, incorrect, all],
                                     layout=layout).to_plotly_json())]


@schema
class PsthDataVarchar(dj.Computed):
    definition = """
    -> ephys.Cluster
    -> ephys.Event
    ---
    psth_x_lim:             varchar(32)
    psth_left=null:         varchar(10000)
    psth_right=null:        varchar(10000)
    psth_incorrect=null:    varchar(10000)
    psth_all=null:          varchar(10000)
    psth_time=null:         varchar(10000)
    -> PsthTemplate
    """
    key_source = ephys.Cluster * (ephys.Event & 'event != "go cue"') & \
        behavior.TrialSet & ephys.TrialSpikes

    def make(self, key):
        trials_all = (behavior.TrialSet.Trial * ephys.TrialSpikes & key).proj(
            'trial_start_time', 'trial_stim_on_time',
            'trial_response_time', 'trial_feedback_time',
            'trial_response_choice', 'trial_spike_times',
            trial_duration='trial_end_time-trial_start_time',
            trial_signed_contrast='trial_stim_contrast_right - trial_stim_contrast_left'
        ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"'

        x_lim = [-1, 1]
        if not len(trials_all):
            self.insert1(dict(
                **key,
                psth_x_lim=','.join('{:0.2f}'.format(x) for x in x_lim),
                psth_template_idx=0))
            return

        trials_left = trials_all & 'trial_response_choice="CW"' \
            & 'trial_signed_contrast < 0'
        trials_right = trials_all & 'trial_response_choice="CCW"' \
            & 'trial_signed_contrast > 0'
        trials_incorrect = trials_all - \
            trials_right.proj() - trials_left.proj()

        align_event = (ephys.Event & key).fetch1('event')

        entry = dict(**key)
        if len(trials_left):
            _, psth_left = putils.compute_psth(
                trials_left, 'left', align_event,
                1000, 10, x_lim, as_dict=False)
            entry.update(
                psth_left=','.join('{:0.5f}'.format(x) for x in psth_left))

        if len(trials_right):
            _, psth_right = putils.compute_psth(
                trials_right, 'right', align_event,
                1000, 10, x_lim, as_dict=False)
            entry.update(
                psth_right=','.join('{:0.5f}'.format(x) for x in psth_right))

        if len(trials_incorrect):
            _, psth_incorrect = putils.compute_psth(
                trials_incorrect, 'incorrect', align_event,
                1000, 10, x_lim, as_dict=False)
            entry.update(
                psth_incorrect=','.join('{:0.5f}'.format(x)
                                        for x in psth_incorrect))

        psth_time, psth_all = putils.compute_psth(
            trials_all, 'all', align_event,
            1000, 10, x_lim, as_dict=False)

        entry.update(
            psth_x_lim=','.join('{:0.2f}'.format(x) for x in x_lim),
            psth_all=','.join('{:0.5f}'.format(x) for x in psth_all),
            psth_time=','.join('{:0.5f}'.format(x) for x in psth_time),
            psth_template_idx=0)

        self.insert1(entry)
