import datajoint as dj
from .. import behavior, ephys
from ..analyses import ephys as ephys_analyses
from . import plotting_utils_ephys as putils
from . import utils
from . import ephys_plotting as eplt
from .figure_model import PngFigure
from .utils import RedBlueColorBar
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import json
from os import path
from tqdm import tqdm
import boto3
import brainbox as bb
from matplotlib.axes import Axes
import seaborn as sns
import colorlover as cl


schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_plotting_ephys')

wheel = dj.create_virtual_module('wheel', 'group_shared_wheel')

# get external bucket
store = dj.config['stores']['plotting']
s3 = boto3.resource(
    's3',
    aws_access_key_id=store['access_key'],
    aws_secret_access_key=store['secret_key'])

bucket = s3.Bucket(store['bucket'])


@schema
class Sorting(dj.Lookup):
    definition = """
    sort_by:     varchar(32)
    """
    contents = zip(['trial_id',
                    'response - stim on',
                    'feedback - stim on',
                    'feedback - response',
                    'movement - stim on',
                    'feedback - movement',
                    'contrast',
                    'feedback type'])


@schema
class ValidAlignSort(dj.Lookup):
    definition = """
    -> ephys.Event
    -> Sorting
    ---
    condition_type='regular' : enum('regular', 'difference')
    wheel_needed             : bool
    relevant_field=''        : varchar(64)
    sorting_variable=''      : varchar(64)  # sorting variable used in the query. e.g. 'trial_feedback_time - trial_stim_on_time'
    mark_variable=''         : varchar(64)  # mark variable for some combinations
    label_variable=''        : varchar(64)  # label variable in the plot
    """
    contents = [
        ['stim on', 'trial_id', 'regular', 0, 'trial_id', 'trial_id', '', ''],
        ['stim on', 'contrast', 'regular', 0, 'trial_signed_contrast',
         'trial_signed_contrast', '', ''],
        ['stim on', 'feedback - stim on', 'difference', 0, '',
         'trial_feedback_time - trial_stim_on_time',
         'trial_feedback_time - trial_stim_on_time', 'feedback'],
        ['stim on', 'movement - stim on', 'difference', 1, '',
         'movement_onset - trial_stim_on_time',
         'movement_onset - trial_stim_on_time', 'movement'],
        ['movement', 'trial_id', 'regular', 1, 'trial_id', 'trial_id', '', ''],
        ['movement', 'movement - stim on', 'difference', 1, '',
         'movement_onset - trial_stim_on_time',
         'trial_stim_on_time - movement_onset', 'stim on'],
        ['movement', 'feedback - movement', 'difference', 1, '',
         'trial_feedback_time - movement_onset',
         'trial_feedback_time - movement_onset', 'feedback'],
        ['feedback', 'trial_id', 'regular', 0, 'trial_id', 'trial_id', '', ''],
        ['feedback', 'feedback type', 'regular', 0,
         'trial_feedback_type', 'trial_feedback_type, trial_id', '', '']
    ]


@schema
class RasterLayoutTemplate(dj.Lookup):
    definition = """
    template_idx:   int
    ---
    raster_data_template:   longblob
    """

    def get_legend(trials_type, legend_group):
        if trials_type == 'left':
            color = 'green'
        elif trials_type == 'right':
            color = 'blue'
        elif trials_type == 'incorrect':
            color = 'red'
        else:
            raise NameError(
                f"""
                Wrong trial type, has to be one of the following: \n
                "left", "right", "incorrect"
                """
            )
        if legend_group == 'spike':
            marker = 'markers'
        else:
            marker = 'lines'

        return go.Scatter(
            x=[5],
            y=[10],
            mode=marker,
            marker=dict(
                size=6,
                color=color,
                opacity=0.5
            ),
            name='{} time on {} trials'.format(legend_group, trials_type),
            legendgroup=legend_group
        )

    legend_left = get_legend('left', 'spike')
    legend_right = get_legend('right', 'spike')
    legend_incorrect = get_legend('incorrect', 'spike')

    legend_mark_left = get_legend('left', 'event')
    legend_mark_right = get_legend('right', 'event')
    legend_mark_incorrect = get_legend('incorrect', 'event')

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

    axis = go.Scatter(
        x=[-1, 1],
        # y=y_lim,
        mode='markers',
        marker=dict(opacity=0),
        showlegend=False
    )
    axis2 = go.Scatter(
        x=[-1, 1],
        # y=y_lim,
        mode='markers',
        marker=dict(opacity=0),
        showlegend=False,
        yaxis='y2'
    )

    # template_0: sorting_var trial_id
    data0 = [axis]
    template_0 = dict(
        template_idx=0,
        raster_data_template=go.Figure(
            data=data0, layout=layout).to_plotly_json())

    # template_1: sorting_var feedback - stim on etc.
    data1 = [axis, legend_left, legend_right, legend_incorrect,
             legend_mark_left, legend_mark_right, legend_mark_incorrect]
    template_1 = dict(
        template_idx=1,
        raster_data_template=go.Figure(
            data=data1, layout=layout).to_plotly_json())

    # template_2: sorting_var contrast
    data2 = [axis2]
    fig = go.Figure(
        data=data2, layout=layout)
    fig.update_layout(
        yaxis2=dict(
            title='Contrast',
            # range=y_lim,
            showgrid=False,
            overlaying='y',
            side='right',
            tickmode='array',
            # tickvals=tick_pos, # from Raster table
            # ticktext=contrasts # from Raster table
        ))
    template_2 = dict(
        template_idx=2,
        raster_data_template=fig.to_plotly_json()
    )

    # template_3: sorting_var feedback type
    incorrect = go.Scatter(
        x=[-2, -1],
        y=[-2, -1],
        fill='tozeroy',
        fillcolor='rgba(218, 59, 70, 0.5)',
        name='Incorrect',
        mode='none'
    )
    correct = go.Scatter(
        x=[-2, -1],
        y=[-2, -1],
        fill='tonexty',
        fillcolor='rgba(65, 124, 168, 0.5)',
        name='Correct',
        mode='none'
    )

    data3 = [axis, incorrect, correct]
    template_3 = dict(
        template_idx=3,
        raster_data_template=go.Figure(
            data=data3, layout=layout).to_plotly_json())

    contents = [
        template_0,
        template_1,
        template_2,
        template_3
    ]


@schema
class Raster(dj.Computed):
    definition = """
    -> ephys.DefaultCluster
    -> ValidAlignSort
    ---
    plotting_data_link=null:      varchar(255)
    plot_ylim:                    blob
    plot_contrasts=null:          blob          # for sorting by contrast, others null
    plot_contrast_tick_pos=null:  blob          # y position of each contrast, for sorting by contrast, others null
    mark_label=null:              varchar(32)
    -> RasterLayoutTemplate
    """
    key_source = ephys.DefaultCluster * ValidAlignSort & behavior.TrialSet & \
        ephys.AlignedTrialSpikes & [{'wheel_needed': 0}, wheel.MovementTimes]

    def plot_empty(ax, x_lim=[-1, 1], y_lim=[0, 2]):
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)

        return ax, x_lim, y_lim

    def plot_regular(trials, key, ax, x_lim=[-1, 1]):

        relevant_field, sorting_variable = (ValidAlignSort & key).fetch1(
            'relevant_field', 'sorting_variable')

        spk_times, field = (trials & key).fetch(
            'trial_spike_times', relevant_field,
            order_by=sorting_variable)

        spk_trial_ids = np.hstack(
            [[trial_id] * len(spk_time)
                for trial_id, spk_time in enumerate(spk_times)])

        ax.plot(np.hstack(spk_times), spk_trial_ids, 'k.', alpha=0.5,
                markeredgewidth=0)

        if key['sort_by'] != 'trial_id':
            # plot different contrasts or different feedback types as background
            values, u_inds = np.unique(field, return_index=True)
            u_inds = list(u_inds) + [len(field)]

            if key['sort_by'] == 'contrast':
                tick_positions = np.add(u_inds[1:], u_inds[:-1])/2
                puor = cl.scales[str(len(values))]['div']['PuOr']
                colors = np.divide(cl.to_numeric(puor), 255)
                alpha = 0.8
            else:
                colors = sns.diverging_palette(10, 240, n=len(values))
                alpha = 0.5

            for i, ind in enumerate(u_inds[:-1]):
                ax.fill_between([-1, 1], u_inds[i], u_inds[i+1]-1,
                                color=colors[i], alpha=alpha)
        # set the limits
        ax.set_xlim(x_lim[0], x_lim[1])

        if len(spk_trial_ids):
            y_lim = max(spk_trial_ids) * 1.02
        else:
            y_lim = 10
        ax.set_ylim(-2, y_lim)

        if key['sort_by'] == 'contrast':
            return ax, x_lim, [-2, y_lim], values, tick_positions
        else:
            return ax, x_lim, [-2, y_lim]

    def plot_difference(trials, key, ax, x_lim=[-1, 1]):

        sorting_variable, mark_variable, label_variable = \
            (ValidAlignSort & key).fetch1(
                'sorting_variable', 'mark_variable', 'label_variable')

        trials_left = trials & 'trial_response_choice="CW"' & \
            'trial_signed_contrast < 0'
        trials_right = trials & 'trial_response_choice="CCW"' & \
            'trial_signed_contrast > 0'
        trials_incorrect = trials - trials_left.proj() - trials_right.proj()

        trial_groups = [
            {'trials': trials_incorrect, 'color': 'r', 'label': 'incorrect trials'},
            {'trials': trials_left,      'color': 'g', 'label': 'left trials'},
            {'trials': trials_right,     'color': 'b', 'label': 'right trials'}
        ]

        base = 0
        for trial_group in trial_groups:

            spk_times, marking_points = \
                (trial_group['trials'].proj(
                    'trial_spike_times',
                    sort=sorting_variable,
                    mark_point=mark_variable) & key).fetch(
                        'trial_spike_times', 'mark_point', order_by='sort')

            if len(spk_times) and len(np.hstack(spk_times)):
                spk_trial_ids = np.hstack(
                    [[trial_id + base] * len(spk_time)
                     for trial_id, spk_time in enumerate(spk_times)])
                ax.plot(np.hstack(spk_times), spk_trial_ids,
                        '{}.'.format(trial_group['color']),
                        alpha=0.5, markeredgewidth=0,
                        label=trial_group['label'])
                ax.plot(marking_points,
                        np.add(range(len(spk_times)), base),
                        trial_group['color'],
                        label=label_variable)
            else:
                spk_trial_ids = [base]
            base = max(spk_trial_ids)

        ax.set_xlim(x_lim[0], x_lim[1])
        y_lim = base * 1.02
        ax.set_ylim(-2, y_lim)

        return ax, x_lim, [-2, y_lim]

    def make(self, key):
        cluster = ephys.DefaultCluster & key
        field_list = [
            'trial_start_time',
            'trial_stim_on_time',
            'trial_response_time',
            'trial_feedback_time',
            'trial_feedback_type',
            'trial_response_choice',
            'trial_spike_times',
        ]
        field_dict = dict(
            trial_duration='trial_end_time-trial_start_time',
            trial_signed_contrast="""trial_stim_contrast_right -
                                        trial_stim_contrast_left"""
        )
        trials = (behavior.TrialSet.Trial *
                  ephys.AlignedTrialSpikes & cluster).proj(
                      *field_list, **field_dict
        ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"' & key

        wheel_needed = (ValidAlignSort & key).fetch1('wheel_needed')

        if wheel_needed:
            trials = (trials * wheel.MovementTimes).proj(
                    ..., 'movement_onset')

        if key['sort_by'] == 'trial_id':
            key['template_idx'] = 0
        elif key['sort_by'] == 'contrast':
            key['template_idx'] = 2
        elif key['sort_by'] == 'feeback type':
            key['template_idx'] = 3
        else:
            key['template_idx'] = 1

        cond_type = (ValidAlignSort & key).fetch1('condition_type')

        if not len(trials):
            draw = Raster.plot_empty
            arg = dict()
        else:
            arg = dict(trials=trials, key=key)
            if cond_type == 'regular':
                draw = Raster.plot_regular
            else:
                draw = Raster.plot_difference

        fig = PngFigure(draw, arg, dpi=60, transparent=True)

        if key['sort_by'] == 'contrast':
            key['plot_contrasts'] = fig.other_returns[0]
            key['plot_contrast_tick_pos'] = fig.other_returns[1]

        fig_link = path.join(
            'raster',
            str(key['subject_uuid']),
            key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            str(key['probe_idx']),
            key['event'],
            key['sort_by'],
            str(key['cluster_id'])) + '.png'

        fig.upload_to_s3(bucket, fig_link)

        key['plotting_data_link'] = fig_link
        key['plot_ylim'] = fig.y_lim
        key['mark_label'] = (ValidAlignSort & key).fetch1('label_variable')

        self.insert1(key)


@schema
class PsthTemplate(dj.Lookup):
    definition = """
    psth_template_idx:   int
    ---
    psth_data_template:  longblob
    """

    left = go.Scatter(
        # x=psth_time, # fetched from the table Psth
        # y=psth_left, # fetched from the table Psth
        mode='lines',
        marker=dict(
            size=6,
            color='green'),
        fill='tonexty',
        fillcolor='rgba(0, 255, 0, 0.2)',
        name='left trials, mean +/- s.e.m.'
    )
    upper_left = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_left_upper), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        fillcolor='rgba(0, 255, 0, 0.2)',
        line=dict(width=0),
        fill='tonexty',
        showlegend=False,
    )
    lower_left = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_left_lower), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        line=dict(width=0),
        showlegend=False,
    )
    right = go.Scatter(
        # x=psth_time, # fetched from the table Psth
        # y=psth_right, # fetched from the table Psth
        mode='lines',
        marker=dict(
            size=6,
            color='blue'),
        fill='tonexty',
        fillcolor='rgba(0, 0, 255, 0.2)',
        name='right trials, mean +/- s.e.m.'
    )
    upper_right = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_right_upper), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        fillcolor='rgba(0, 0, 255, 0.2)',
        line=dict(width=0),
        fill='tonexty',
        showlegend=False,
    )
    lower_right = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_right_lower), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        line=dict(width=0),
        showlegend=False,
    )
    incorrect = go.Scatter(
        # x=psth_time, # fetched from the table Psth
        # y=psth_incorrect, # fetched from the table Psth
        mode='lines',
        marker=dict(
            size=6,
            color='red'),
        fillcolor='rgba(255, 0, 0, 0.2)',
        fill='tonexty',
        name='incorrect trials, mean +/- s.e.m.'
    )
    upper_incorrect = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_incorrect_upper), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        fillcolor='rgba(255, 0, 0, 0.2)',
        line=dict(width=0),
        fill='tonexty',
        showlegend=False,
    )
    lower_incorrect = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_incorrect_lower), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        line=dict(width=0),
        showlegend=False,
    )
    all = go.Scatter(
        # x=psth_time, # fetched from the table Psth
        # y=psth_all, # fetched from the table Psth
        mode='lines',
        marker=dict(
            size=6,
            color='black'),
        fill='tonexty',
        fillcolor='rgba(0, 0, 0, 0.2)',
        name='all trials, mean +/- s.e.m.'
    )
    upper_all = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_all_upper), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        fillcolor='rgba(0, 0, 0, 0.2)',
        line=dict(width=0),
        fill='tonexty',
        showlegend=False,
    )
    lower_all = go.Scatter(
        # x=list(psth_time), # fetched from the table Psth
        # y=list(psth_all_lower), # fetched from the table Psth
        mode='lines',
        marker=dict(color="#444"),
        line=dict(width=0),
        showlegend=False,
    )

    layout = go.Layout(
        width=700,
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

    contents = [
        dict(psth_template_idx=0,
             psth_data_template=go.Figure(
                 data=[left, right, incorrect, all],
                 layout=layout).to_plotly_json()),
        dict(psth_template_idx=1,
             psth_data_template=go.Figure(
                 data=[lower_left, left, upper_left,
                       lower_right, right, upper_right,
                       lower_incorrect, incorrect, upper_incorrect,
                       lower_all, all, upper_all],
                 layout=layout).to_plotly_json()
             )
        ]


@schema
class Psth(dj.Computed):
    definition = """
    -> ephys.DefaultCluster
    -> ephys.Event
    ---
    psth_x_lim:                 varchar(32)
    psth_left=null:             varchar(1000)
    psth_left_upper=null:       varchar(1000)
    psth_left_lower=null:       varchar(1000)
    psth_right=null:            varchar(1000)
    psth_right_upper=null:      varchar(1000)
    psth_right_lower=null:      varchar(1000)
    psth_incorrect=null:        varchar(1000)
    psth_incorrect_upper=null:  varchar(1000)
    psth_incorrect_lower=null:  varchar(1000)
    psth_all=null:              varchar(1000)
    psth_all_upper=null:        varchar(1000)
    psth_all_lower=null:        varchar(1000)
    psth_time=null:             varchar(1000)
    psth_ts=CURRENT_TIMESTAMP:  timestamp
    -> PsthTemplate
    """
    key_source = ephys.DefaultCluster * (ephys.Event & 'event in ("stim on", "movement", "feedback")') & \
        behavior.TrialSet & ephys.AlignedTrialSpikes

    def make(self, key):
        trials_all = (behavior.TrialSet.Trial * ephys.AlignedTrialSpikes & key).proj(
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
            _, psth_left, psth_left_upper, psth_left_lower = \
                putils.compute_psth_with_errorbar(
                    trials_left, 'left', align_event, as_plotly_obj=False)
            entry.update(
                psth_left=','.join('{:0.5f}'.format(x) for x in psth_left),
                psth_left_upper=','.join('{:0.5f}'.format(x) for x in psth_left_upper),
                psth_left_lower=','.join('{:0.5f}'.format(x) for x in psth_left_lower))

        if len(trials_right):
            _, psth_right, psth_right_upper, psth_right_lower = \
                putils.compute_psth_with_errorbar(
                    trials_right, 'right', align_event, as_plotly_obj=False)
            entry.update(
                psth_right=','.join('{:0.5f}'.format(x)
                                    for x in psth_right),
                psth_right_upper=','.join('{:0.5f}'.format(x)
                                          for x in psth_right_upper),
                psth_right_lower=','.join('{:0.5f}'.format(x)
                                          for x in psth_right_lower))

        if len(trials_incorrect):
            _, psth_incorrect, psth_incorrect_upper, psth_incorrect_lower = \
                putils.compute_psth_with_errorbar(
                    trials_incorrect, 'incorrect', align_event, as_plotly_obj=False)
            entry.update(
                psth_incorrect=','.join('{:0.5f}'.format(x)
                                        for x in psth_incorrect),
                psth_incorrect_upper=','.join('{:0.5f}'.format(x)
                                              for x in psth_incorrect_upper),
                psth_incorrect_lower=','.join('{:0.5f}'.format(x)
                                              for x in psth_incorrect_lower))

        psth_time, psth_all, psth_all_upper, psth_all_lower = \
            putils.compute_psth_with_errorbar(
                trials_all, 'all', align_event, as_plotly_obj=False)

        entry.update(
            psth_x_lim=','.join('{:0.2f}'.format(x) for x in x_lim),
            psth_all=','.join('{:0.5f}'.format(x) for x in psth_all),
            psth_all_upper=','.join('{:0.5f}'.format(x) for x in psth_all_upper),
            psth_all_lower=','.join('{:0.5f}'.format(x) for x in psth_all_lower),
            psth_time=','.join('{:0.5f}'.format(x) for x in psth_time),
            psth_template_idx=1)

        self.insert1(entry)


@schema
class DepthRasterTemplate(dj.Lookup):
    definition = """
    depth_raster_template_idx:    int
    ---
    depth_raster_template: longblob
    """
    axis = go.Scatter(
        # x=plot_xlim, # fetched from DepthRaster
        # y=plot_ylim, # fetched from DepthRaster
        mode='markers',
        marker=dict(opacity=0),
        showlegend=False,
    )

    first_trial_mark = go.Scatter(
        # x=[first_start, first_start], # first_start fetched from DepthRaster
        # y=[plot_ylim[1]-20, plot_ylim[1]-80], # fetched from DepthRaster
        mode='lines',
        line=dict(
            color='rgba(20, 40, 255, 1)',
            width=1.5),
        name='Start of the first trial'
    )
    last_trial_mark = go.Scatter(
        # x=[last_end, last_end], # last_end fetched from DepthRaster
        # y=[y_lim[1]-20, y_lim[1]-80], # fetched from DepthRaster
        mode='lines',
        line=dict(
            color='rgba(255, 20, 20, 1)',
            width=1.5),
        name='End of the last trial'
    )

    layout1 = go.Layout(
        images=[dict(
            source='',  # to be replaced by the s3 link
            # sizex=plot_xlim[1] - plot_xlim[0], # fetched from Driftmap
            # sizey=plot_ylim[1] - plot_ylim[0], # fetched from Driftmap
            # x=x_lim[0], # fetched from Driftmap
            # y=y_lim[1], # fetched from Driftmap
            xref='x',
            yref='y',
            sizing='stretch',
            layer='below'
            )],
        width=900,
        height=900,
        margin=go.layout.Margin(
            l=50,
            r=30,
            b=40,
            t=80,
            pad=0
        ),
        title=dict(
            text='Depth raster of the entire session',
            x=0.45,
            y=0.95
        ),
        xaxis=dict(
            title='Time (sec)',
            # range=plot_xlim,  # fetched from DepthRaster
            showgrid=False
        ),
        yaxis=dict(
            title='Distance from the probe tip (µm)',
            # range=plot_ylim,  # fetched from DepthRaster
            showgrid=False
        ))

    trial_stim_on_mark = go.Scatter(
        # x=[trial_stim_on, trial_stim_on], # fetched from DepthRasterPerTrial
        # y=plot_ylim, # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(20, 40, 255, 0.4)',
            width=1.5),
        name='Stim on'
    )

    trial_movement_mark = go.Scatter(
        # x=[trial_movement, trial_movement], # fetched from DepthRasterPerTrial
        # y=plot_ylim, # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(200, 40, 25, 0.4)',
            width=1.5),
        name='Movement'
    )

    trial_feedback_mark = go.Scatter( # if null, skip this line
        # x=[trial_feedback, trial_feedback], # fetched from DepthRasterPerTrial
        # y=plot_ylim, # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(60, 255, 10, 0.4)',
            width=1.5),
        name='Feedback'
    )

    trial_stim_off_mark = go.Scatter(
        # x=[trial_stim_off, trial_stim_off], # fetched from DepthRasterPerTrial
        # y=plot_ylim, # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(230, 190, 20, 0.8)',
            width=1.5),
        name='Stim off'
    )

    layout2 = go.Layout(
        images=[dict(
            source='',  # to be replaced by the s3 link
            # sizex=plot_xlim[1] - plot_xlim[0], # fetched from DepthRasterPerTrial
            # sizey=plot_ylim[1] - plot_ylim[0], # fetched from DepthRasterPerTrial
            # x=x_lim[0], # fetched from DriftmapTrial
            # y=y_lim[1], # fetched from Driftmap
            xref='x',
            yref='y',
            sizing='stretch',
            layer='below'
            )],
        width=1100,
        height=800,
        margin=go.layout.Margin(
            l=50,
            r=30,
            b=40,
            t=80,
            pad=0
        ),
        title=dict(
            # text=plot_title, # fetched from DepthRasterPerTrial
            x=0.45,
            y=0.95
        ),
        xaxis=dict(
            title='Time (sec)',
            # range=plot_xlim,  # fetched from DepthRasterPerTrial
            showgrid=False
        ),
        yaxis=dict(
            title='Depth relative to the probe tip (µm)',
            # range=plot_ylim,  # fetched from DepthRasterPerTrial
            showgrid=False
        ))

    data1 = [axis, first_trial_mark, last_trial_mark]
    data2 = [axis, trial_stim_on_mark, trial_movement_mark,
             trial_feedback_mark, trial_stim_off_mark]
    contents = [
        dict(depth_raster_template_idx=0,
             depth_raster_template=go.Figure(
                 data=data1,
                 layout=layout1).to_plotly_json()),
        dict(depth_raster_template_idx=1,
             depth_raster_template=go.Figure(
                 data=data2,
                 layout=layout2).to_plotly_json())]


@schema
class DepthRaster(dj.Computed):
    definition = """
    -> ephys.ProbeInsertion
    ---
    plotting_data_link=null              : varchar(255)
    plotting_data_link_low_res=null      : varchar(255)
    plotting_data_link_very_low_res=null : varchar(255)
    plot_ylim                            : blob
    plot_xlim                            : blob
    first_start                          : float
    last_end                             : float
    -> DepthRasterTemplate
    """
    key_source = ephys.ProbeInsertion & ephys.DefaultCluster

    def make(self, key):

        spikes_data = putils.prepare_spikes_data(key)

        link = path.join(
            'depthraster_session',
            str(key['subject_uuid']),
            key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            str(key['probe_idx']))

        fig_link_full = link + '.png'
        fig_link_low = link + '_low.png'
        fig_link_very_low = link + '_very_low.png'

        trials = (behavior.TrialSet.Trial & key).fetch()

        key['plot_xlim'], key['plot_ylim'] = \
            putils.create_driftmap_plot(
                spikes_data,
                fig_dir=fig_link_full, store_type='s3')

        putils.create_driftmap_plot(
            spikes_data, dpi=25, fig_dir=fig_link_low,
            store_type='s3')

        putils.create_driftmap_plot(
            spikes_data, dpi=10, fig_dir=fig_link_very_low,
            store_type='s3')

        key.update(
            plotting_data_link=fig_link_full,
            plotting_data_link_low_res=fig_link_low,
            plotting_data_link_very_low_res=fig_link_very_low,
            first_start=trials[0]['trial_start_time'],
            last_end=trials[-1]['trial_end_time'],
            depth_raster_template_idx=0
        )

        self.insert1(key)


@schema
class TrialType(dj.Lookup):
    definition = """
    trial_type:       varchar(32)
    """
    contents = zip(['Correct Left Contrast',
                    'Correct Right Contrast',
                    'Incorrect Left Contrast',
                    'Incorrect Right Contrast',
                    'Correct All'])


@schema
class DepthRasterExampleTrial(dj.Computed):
    definition = """
    # Depth Raster for example trials
    -> ephys.ProbeInsertion
    -> behavior.TrialSet.Trial
    ---
    plotting_data_link=null:      varchar(255)
    plot_ylim:                    blob
    plot_xlim:                    blob
    plot_title:                   varchar(64)
    trial_stim_on:                float
    trial_stim_off:               float
    trial_movement=null:          float     # movement onset
    trial_feedback=null:          float
    trial_contrast:               float     # signed contrast
    -> TrialType                  # type of trial
    -> DepthRasterTemplate
    """
    key_source = ephys.ProbeInsertion & behavior.TrialSet & \
        ephys.DefaultCluster & wheel.MovementTimes

    def _get_trial_type(self, trial):

        if trial['trial_response_choice'] == 'CW' and \
                trial['trial_feedback_type'] == 1:
            return 'Correct Left Contrast'

        elif trial['trial_response_choice'] == 'CCW' and \
                trial['trial_feedback_type'] == 1:
            return 'Correct Right Contrast'

        elif trial['trial_response_choice'] == 'CW' and \
                trial['trial_feedback_type'] == -1:
            return 'Incorrect Left Contrast'

        elif trial['trial_response_choice'] == 'CCW' and \
                trial['trial_feedback_type'] == -1:
            return 'Incorrect Right Contrast'

        else:
            return None

    def _create_trial_raster(self, key, spikes_data, trial):

        trial_type = self._get_trial_type(trial)
        f = np.logical_and(
            spikes_data['spikes_times'] < trial['trial_end_time'],
            spikes_data['spikes_times'] > trial['trial_start_time'])

        spikes_data_trial = dict(
            spikes_depths=spikes_data['spikes_depths'][f],
            spikes_times=spikes_data['spikes_times'][f],
            spikes_amps=spikes_data['spikes_amps'][f],
            spikes_clusters=spikes_data['spikes_clusters'][f],
            clusters_depths=spikes_data['clusters_depths']
        )

        fig_link = path.join(
            'depthraster_session',
            str(key['subject_uuid']),
            key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            str(key['probe_idx']), str(trial['trial_id'])) + '.png'

        key['plot_xlim'], key['plot_ylim'] = \
            putils.create_driftmap_plot(
                spikes_data_trial, dpi=100, figsize=[18, 12],
                fig_dir=fig_link, store_type='s3')

        fb_time = trial['trial_feedback_time']
        movement_time = trial['movement_onset']

        depth_raster = dict(
            **key,
            plotting_data_link=fig_link,
            trial_stim_on=trial['trial_stim_on_time'],
            trial_stim_off=(fb_time if fb_time else movement_time) +
                           (1 if trial['trial_feedback_type'] > 0 else 2),
            trial_feedback=fb_time,
            trial_movement=movement_time,
            trial_id=trial['trial_id'],
            depth_raster_template_idx=1,
            trial_type=trial_type,
            trial_contrast=trial['trial_signed_contrast'],
            plot_title='Depth Raster for a ' + trial_type + ' ' +
                       str(trial['trial_signed_contrast'])
        )

        return depth_raster

    def make(self, key):

        mode = 'all'
        spikes_data = putils.prepare_spikes_data(key)

        # pick some example trials and generate depth raster
        trials_all = (behavior.TrialSet.Trial * wheel.MovementTimes & key).proj(
            'trial_response_choice',
            'trial_feedback_type',
            'trial_stim_on_time',
            'movement_onset',
            'trial_feedback_time',
            'trial_start_time',
            'trial_end_time',
            trial_duration='trial_end_time-trial_start_time',
            trial_signed_contrast='trial_stim_contrast_right - trial_stim_contrast_left'
        ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"'

        trials_depthraster = []
        if mode == 'example':

            conditions = [
                {'trial_response_choice': 'CW', 'trial_feedback_type': 1},
                {'trial_response_choice': 'CCW', 'trial_feedback_type': 1},
                {'trial_response_choice': 'CW', 'trial_feedback_type': -1},
                {'trial_response_choice': 'CCW', 'trial_feedback_type': -1},
            ]

            trial_num = 3

            for contrast in tqdm(dj.U('trial_signed_contrast') & trials_all,
                                 position=0):

                for cond in conditions:
                    trials_cond = (trials_all & cond & contrast).fetch()
                    if len(trials_cond):
                        trials = np.random.choice(trials_cond,
                                                  size=[trial_num])

                        for trial in trials:
                            trials_depthraster.append(
                                self._create_trial_raster(
                                    key, spikes_data, trial))

        else:
            for trial_key in tqdm(trials_all.fetch('KEY'), position=0):
                trial = (trials_all & trial_key).fetch1()
                trial_type = self._get_trial_type(trial)
                if trial_type:
                    trials_depthraster.append(
                        self._create_trial_raster(key, spikes_data, trial))

        try:
            self.insert(trials_depthraster, skip_duplicates=True)
        except Exception:
            print('Failed to insert all trials at once, \
                    try inserting one by one...')
            for trial_dr in trials_depthraster:
                self.insert1(trial_dr, skip_duplicates=True)


@schema
class DepthPethTemplate(dj.Lookup):
    definition = """
    depth_peth_template_idx:    int
    ---
    depth_peth_template: longblob
    """

    data = [
        dict(
            # x=[plot_xlim[0]-0.2, plot_xlim[0]-0.1],   # plot_xlim from DepthPeth
            # y=[plot_ylim[0]-0.2], # plot_ylim from DepthPeth
            # z=z_range,   # z_range from DepthPeth
            type='heatmap',
            colorbar=dict(
                thickness=10,
                title='(Firing rate - baseline)/(baseline + 1)',
                titleside='right'),
            # colorscale=color_scale        # color_scale from DepthPeth
        )]

    layout = go.Layout(
        images=[dict(source='',  # to be replaced by s3 link in Depth
                     # sizex=plot_xlim[1] - plot_xlim[0],   # plot_xlim from DepthPeth
                     # sizey=plot_ylim[1] - plot_ylim[0],   # plot_ylim from DepthPeth
                     # x=plot_xlim[0],  # plot_xlim from DepthPeth
                     # y=plot_ylim[1],  # plot_ylim from DepthPeth
                     xref='x',
                     yref='y',
                     sizing='stretch',
                     layer='below')],
        xaxis=dict(
            title='Time (s)',
            showgrid=False,
            # range=plot_xlim    # plot_xlim from DepthPeth
            ),
        yaxis=dict(
            title='Depth from the probe tip (µm)',
            showgrid=False,
            # range=plot_ylim    # plot_ylim from DepthPeth
        ),
        width=600,
        height=480,
        title=dict(
            # text='Depth PETH, aligned to {} time'.format(event),   # event from DepthPeth
            x=0.5,
            y=0.85
        ),
        legend=dict(
            x=1.2,
            y=0.8,
            orientation='v'
        ),
        template=dict(
            layout=dict(
                plot_bgcolor="white")))

    contents = [
        dict(depth_peth_template_idx=0,
             depth_peth_template=go.Figure(
                data=data,
                layout=layout).to_plotly_json())]


@schema
class DepthPeth(dj.Computed):
    definition = """
    -> ephys_analyses.NormedDepthPeth
    ---
    plotting_data_link          : varchar(255)
    plot_ylim                   : blob
    plot_xlim                   : blob
    z_range                     : blob
    color_scale                 : longblob
    -> DepthPethTemplate
    """

    def make(self, key):
        normed_peth, depths, time = \
            (ephys_analyses.DepthPeth *
             ephys_analyses.NormedDepthPeth & key).fetch1(
                'normed_peth', 'depth_bin_centers', 'time_bin_centers')

        peth_df = pd.DataFrame(normed_peth, columns=np.round(time, decimals=2),
                               index=depths.astype('int'))
        min_val = np.min(normed_peth)
        max_val = np.max(normed_peth)

        rb_cmap = RedBlueColorBar(max_val, min_val)

        fig = PngFigure(eplt.depth_peth, dict(peth_df=peth_df),
                        dict(colors=rb_cmap.as_matplotlib(),
                             as_background=True,
                             return_lims=True))

        fig_link = path.join(
            'depthpeth_session',
            str(key['subject_uuid']),
            key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            str(key['probe_idx'])) + '_' + key['event'] + '_' + key['trial_type'] + '.png'

        fig.upload_to_s3(bucket, fig_link)

        self.insert1(
            dict(**key,
                 plotting_data_link=fig_link,
                 plot_ylim=fig.y_lim,
                 plot_xlim=fig.x_lim,
                 z_range=rb_cmap.zrange,
                 color_scale=rb_cmap.as_plotly(),
                 depth_peth_template_idx=0))

        fig.cleanup()


@schema
class SpikeAmpTimeTemplate(dj.Lookup):
    definition = """
    spike_amp_time_template_idx     : int
    ---
    spike_amp_time_template         : longblob
    """
    axis = go.Scatter(
        # x=plot_ylim,
        # y=plot_ylim,
        mode='markers',
        marker=dict(opacity=0),
        showlegend=False,
    )

    layout = go.Layout(
        images=[dict(source='', # to be replaced by url
                     #  sizex=plot_xlim[1] - plot_xlim[0],
                     #  sizey=plot_ylim[1] - plot_ylim[0],
                     #  x=plot_xlim[0],
                     #  y=plot_ylim[1],
                     xref='x',
                     yref='y',
                     sizing='stretch',
                     layer='below')],
        xaxis=dict(
            title='Time (s)',
            showgrid=False,
            # range=plot_xlim,
            ticks='outside'),
        yaxis=dict(
            title=dict(text='Spike amp (µV)', standoff=10),
            showgrid=False,
            # range=plot_ylim,
            ticks='outside'),

        width=580,
        height=400,
        title=dict(
            text='Spike amp - time',
            x=0.5,
            y=0.85
        ),
        legend=dict(
            x=1.2,
            y=0.8,
            orientation='v'
        ),
        template=dict(
            layout=dict(plot_bgcolor="white")))

    contents = [
        dict(spike_amp_time_template_idx=0,
             spike_amp_time_template=go.Figure(
                data=axis,
                layout=layout).to_plotly_json())]


@schema
class SpikeAmpTime(dj.Computed):
    definition = """
    -> ephys.DefaultCluster
    ---
    plotting_data_link          : varchar(255)
    plot_ylim                   : blob
    plot_xlim                   : blob
    -> SpikeAmpTimeTemplate
    """
    key_source = ephys.ProbeInsertion & ephys.DefaultCluster

    def make(self, key):

        entries = []
        keys, clusters_spike_times, clusters_spike_amps = \
            (ephys.DefaultCluster & key).fetch(
                'KEY', 'cluster_spikes_times', 'cluster_spikes_amps')

        for ikey, spike_times, spike_amps in tqdm(zip(keys,
                                                      clusters_spike_times,
                                                      clusters_spike_amps),
                                                  position=0):
            fig = PngFigure(eplt.spike_amp_time,
                            data=dict(spike_times=spike_times,
                                      spike_amps=spike_amps*1e6),
                            ax_kwargs=dict(s=8,
                                           as_background=True,
                                           return_lims=True),
                            dpi=100, figsize=[10, 5])

            fig_link = path.join(
                'raster',
                str(ikey['subject_uuid']),
                ikey['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
                str(ikey['probe_idx']),
                str(ikey['cluster_id'])) + '.png'

            fig.upload_to_s3(bucket, fig_link)

            entries.append(
                dict(**ikey,
                     plotting_data_link=fig_link,
                     plot_xlim=fig.x_lim,
                     plot_ylim=fig.y_lim,
                     spike_amp_time_template_idx=0).copy())

            fig.cleanup()

        self.insert(entries)


@schema
class AutoCorrelogramTemplate(dj.Lookup):
    definition = """
    acg_template_idx    : int
    ---
    acg_template        : longblob
    """
    data = dict(
        # x=np.linspace(t_start, t_end, len(acg)) * 1000,   # t_start, t_end, acg fetched from AutoCorrelogram
        # y=acg,                # fetched from AutoCorrelogram
        name='data',
        type='scatter',
        marker=dict(
            color='rgba(51, 76.5, 204, 0.8)'
        ),
        x0=0
    )

    layout = dict(
        width=580,
        height=400,
        title=dict(
            text='Autocorrelogram',
            x=0.5,
            y=0.85),
        xaxis=dict(
            title='Lag (ms)',
            showgrid=False,
            linecolor='lightgray',
            anchor='y',
            position=0,
            linewidth=2,
            zeroline=True,
            zerolinecolor='lightgray',
            tickcolor='lightgray',
            ticks='outside',
            tickwidth=2
        ),

        yaxis=dict(
            title='Spike counts',
            showgrid=False,
            # range=plot_ylim    # fetched from AutoCorrelogram
        ),
        plot_bgcolor='rgba(0,0,0,0)'
    )

    contents = [
        dict(acg_template_idx=0,
             acg_template=go.Figure(
                data=data,
                layout=layout).to_plotly_json())]


@schema
class AutoCorrelogram(dj.Computed):
    definition = """
    -> ephys.DefaultCluster
    ---
    acg=''              : varchar(2000)
    t_start             : float
    t_end               : float
    plot_ylim           : blob
    -> AutoCorrelogramTemplate
    """

    def _acorr(self, spike_times, bin_size=None, window_size=None):
        """Compute the auto-correlogram of a neuron.
        Parameters
        ----------
        :param spike_times: Spike times in seconds.
        :type spike_times: array-like
        :param bin_size: Size of the bin, in seconds.
        :type bin_size: float
        :param window_size: Size of the window, in seconds.
        :type window_size: float
        Returns an `(winsize_samples,)` array with the auto-correlogram.
        """
        xc = bb.population.xcorr(
            spike_times, np.zeros_like(spike_times).astype('int'),
            bin_size=bin_size, window_size=window_size)
        return xc[0, 0, :]

    def make(self, key):

        spike_times = (ephys.DefaultCluster & key).fetch1(
            'cluster_spikes_times')

        win_sz = 0.04
        entry = dict(**key,
                     t_start=-win_sz/2,
                     t_end=win_sz/2,
                     plot_ylim=[0, 10],
                     acg_template_idx=0)

        if len(spike_times):
            acg = self._acorr(spike_times, bin_size=0.0002, window_size=win_sz)
            entry.update(
                acg=','.join('{:d}'.format(x) for x in acg),
                plot_ylim=[0, max(acg)+10])

        self.insert1(entry)


@schema
class WaveformTemplate(dj.Lookup):
    definition = """
    waveform_template_idx   : int
    ---
    waveform_template       :  longblob
    """
    axis = go.Scatter(
        # x=plot_xlim,  # fetch from WaveForm
        # y=plot_ylim,  # fetch from WaveForm
        mode='markers',
        marker=dict(opacity=0),
        showlegend=False,
    )

    layout = go.Layout(
        images=[dict(source='',  # replace with plotting_fig_link from Waveform
                     #  sizex=plot_xlim[1] - plot_xlim[0],
                     #  sizey=plot_ylim[1] - plot_ylim[0],
                     #  x=plot_xlim[0],
                     #  y=plot_ylim[1],
                     xref='x',
                     yref='y',
                     sizing='stretch',
                     layer='below')],
        width=580,
        height=400,
        title=dict(
            text='Template waveforms',
            x=0.55,
            y=0.85
        ),
        margin=go.layout.Margin(
            l=100,
            r=30,
            b=40,
            t=80,
            pad=0),
        legend=dict(
            x=1.2,
            y=0.8,
            orientation='v'
        ),
        yaxis=dict(
            title=dict(text='Channel position y (µm)', standoff=10),
            showgrid=False,
            # range=plot_ylim,  # from Waveform
            tickcolor='gray',
            ticks='outside',
            tickwidth=2,
            zeroline=False
        ),

        xaxis=dict(
            title='Channel position x (µm)',
            showgrid=False,
            # range=plot_xlim,  # from Waveform
            ticks='outside',
            tickcolor='gray',
            tickwidth=2,
            zeroline=False
        ),
        plot_bgcolor='rgba(0,0,0,0)')

    contents = [
        dict(waveform_template_idx=0,
             waveform_template=go.Figure(
                 data=axis, layout=layout).to_plotly_json())]


@schema
class Waveform(dj.Computed):
    definition = """
    -> ephys.DefaultCluster
    ---
    plotting_data_link          : varchar(255)
    plot_ylim                   : blob
    plot_xlim                   : blob
    -> WaveformTemplate
    """
    key_source = ephys.ProbeInsertion & ephys.DefaultCluster

    def make(self, key):

        entries = []
        keys, clusters_waveforms, clusters_waveforms_channels = \
            (ephys.DefaultCluster() & key).fetch(
                'KEY', 'cluster_waveforms', 'cluster_waveforms_channels')

        for ikey, waveforms, waveforms_channels in tqdm(
                zip(keys, clusters_waveforms, clusters_waveforms_channels),
                position=0):

            # get channel locations
            channel_coords = (ephys.ChannelGroup() & ikey).fetch1(
                'channel_local_coordinates')
            coords = channel_coords[waveforms_channels]

            fig = PngFigure(
                eplt.template_waveform,
                data=dict(waveforms=waveforms*1e6, coords=coords),
                ax_kwargs=dict(as_background=True, return_lims=True),
                dpi=100, figsize=[5.8, 4])

            fig_link = path.join(
                    'waveform',
                    str(ikey['subject_uuid']),
                    ikey['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
                    str(ikey['probe_idx']),
                    str(ikey['cluster_id'])) + '.png'

            fig.upload_to_s3(bucket, fig_link)

            entries.append(
                dict(**ikey,
                     plotting_data_link=fig_link,
                     plot_xlim=fig.x_lim,
                     plot_ylim=fig.y_lim,
                     waveform_template_idx=0).copy())
            fig.cleanup()

        self.insert(entries)
