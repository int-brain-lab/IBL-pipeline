import datajoint as dj
from .. import behavior, ephys
from . import plotting_utils_ephys as putils
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import json
from os import path
from tqdm import tqdm

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
                    'feedback - response',
                    'contrast',
                    'feedback type'])


@schema
class ValidAlignSort(dj.Lookup):
    definition = """
    -> ephys.Event
    -> Sorting
    """
    contents = [
        ['stim on', 'trial_id'],
        ['stim on', 'contrast'],
        ['stim on', 'feedback - stim on'],
        ['feedback', 'trial_id'],
        ['feedback', 'feedback type']
    ]


@schema
class RasterLayoutTemplate(dj.Lookup):
    definition = """
    template_idx:   int
    ---
    raster_data_template:   longblob
    """

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
        ephys.AlignedTrialSpikes & \
        [dict(event='stim on', sort_by='trial_id'),
         dict(event='stim on', sort_by='contrast'),
         dict(event='stim on', sort_by='feedback - stim on'),
         dict(event='feedback', sort_by='trial_id'),
         dict(event='feedback', sort_by='feedback type')]

    def make(self, key):
        cluster = ephys.DefaultCluster & key
        trials = \
            (behavior.TrialSet.Trial * ephys.AlignedTrialSpikes & cluster).proj(
                'trial_start_time', 'trial_stim_on_time',
                'trial_response_time',
                'trial_feedback_time',
                'trial_feedback_type',
                'trial_response_choice',
                'trial_spike_times',
                trial_duration='trial_end_time-trial_start_time',
                trial_signed_contrast="""trial_stim_contrast_right -
                                         trial_stim_contrast_left"""
            ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"' & key

        if not len(trials):
            if key['sort_by'] == 'trial_id':
                key['template_idx'] = 0
            elif key['sort_by'] == 'contrast':
                key['template_idx'] = 2
            elif key['sort_by'] == 'feeback type':
                key['template_idx'] = 3
            else:
                key['template_idx'] = 1
            self.insert1(dict(
                **key, plot_ylim=[0, 3]))
            return

        align_event = (ephys.Event & key).fetch1('event')
        sorting_var = (Sorting & key).fetch1('sort_by')

        fig_link = path.join(
            'raster',
            str(key['subject_uuid']),
            key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            str(key['probe_idx']),
            key['event'],
            key['sort_by'],
            str(key['cluster_id'])) + '.png'

        if key['sort_by'] == 'contrast':
            y_lim, label, contrasts, tick_pos = \
                putils.create_raster_plot_combined(
                    trials, align_event,
                    sorting_var, fig_dir=fig_link, store_type='s3')
            key['plot_contrasts'] = contrasts
            key['plot_contrast_tick_pos'] = tick_pos
        else:
            y_lim, label = putils.create_raster_plot_combined(
                trials, align_event,
                sorting_var, fig_dir=fig_link, store_type='s3')

        key['plotting_data_link'] = fig_link
        key['plot_ylim'] = y_lim
        key['mark_label'] = label

        if key['sort_by'] == 'trial_id':
            key['template_idx'] = 0
        elif key['sort_by'] == 'contrast':
            key['template_idx'] = 2
        elif key['sort_by'] == 'feedback type':
            key['template_idx'] = 3
        else:
            key['template_idx'] = 1
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
    -> PsthTemplate
    """
    key_source = ephys.DefaultCluster * (ephys.Event & 'event in ("stim on", "feedback")') & \
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
            title='Distance from the probe tip (um)',
            # range=plot_ylim,  # fetched from DepthRaster
            showgrid=False
        ))

    trial_start_mark = go.Scatter(
        # x=[trial_start, trial_start],  # fetched from DepthRasterPerTrial
        # y=plot_ylim,  # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(20, 40, 255, 0.4)',
            width=1.5),
        name='Trial start'
    )
    trial_end_mark = go.Scatter(
        # x=[trial_end, trial_end], # fetched from DepthRasterPerTrial
        # y=plot_ylim, # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(255, 20, 20, 0.4)',
            width=1.5),
        name='Trial end'
    )

    trial_stim_on_mark = go.Scatter(
        # x=[trial_stim_on, trial_stim_on], # fetched from DepthRasterPerTrial
        # y=plot_ylim, # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(200, 40, 255, 0.4)',
            width=1.5),
        name='Stim on')

    trial_feedback_mark = go.Scatter( # if null, skip this line
        # x=[trial_feedback, trial_feedback], # fetched from DepthRasterPerTrial
        # y=plot_ylim, # fetched from DepthRasterPerTrial
        mode='lines',
        line=dict(
            color='rgba(60, 255, 10, 0.4)',
            width=1.5),
        name='Feedback'
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
        width=720,
        height=480,
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
            y=0.9
        ),
        xaxis=dict(
            title='Time (sec)',
            # range=plot_xlim,  # fetched from DepthRasterPerTrial
            showgrid=False
        ),
        yaxis=dict(
            title='Depth relative to the probe tip (um)',
            # range=plot_ylim,  # fetched from DepthRasterPerTrial
            showgrid=False
        ))

    data1 = [axis, first_trial_mark, last_trial_mark]
    data2 = [axis, trial_start_mark, trial_stim_on_mark,
             trial_feedback_mark, trial_end_mark]
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
    plotting_data_link=null:      varchar(255)
    plot_ylim:                    blob
    plot_xlim:                    blob
    first_start:                  float
    last_end:                     float
    -> DepthRasterTemplate
    """
    key_source = ephys.ProbeInsertion & ephys.DefaultCluster

    def make(self, key):

        spikes_data = putils.prepare_spikes_data(key)

        fig_link = path.join(
            'depthraster_session',
            str(key['subject_uuid']),
            key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            str(key['probe_idx'])) + '.png'

        trials = (behavior.TrialSet.Trial & key).fetch()

        key['plot_xlim'], key['plot_ylim'] = \
            putils.create_driftmap_plot(
                spikes_data,
                fig_dir=fig_link, store_type='s3')

        key.update(
            plotting_data_link=fig_link,
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
                    'Incorrect Right Contrast'])


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
    trial_start:                  float
    trial_end:                    float
    trial_stim_on:                float
    trial_feedback=null:          float
    trial_contrast:               float     # signed contrast of
    -> TrialType                  # type of trial
    -> DepthRasterTemplate
    """
    key_source = ephys.ProbeInsertion & behavior.TrialSet & \
        ephys.DefaultCluster

    def create_trial_raster(self, key, spikes_data, trial,
                            trial_type, contrast):
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
                spikes_data, dpi=100, figsize=[18, 12],
                fig_dir=fig_link, store_type='s3')

        depth_raster = dict(
            **key,
            plotting_data_link=fig_link,
            trial_start=trial['trial_start_time'],
            trial_end=trial['trial_end_time'],
            trial_stim_on=trial['trial_stim_on_time'],
            trial_id=trial['trial_id'],
            depth_raster_template_idx=1,
            trial_type=trial_type,
            trial_contrast=contrast['trial_signed_contrast'],
            plot_title='Depth Raster for a ' + trial_type + ' ' + str(contrast['trial_signed_contrast'])
        )

        if not np.isnan(trial['trial_feedback_time']):
            depth_raster.update(
                trial_feedback=trial['trial_feedback_time']
            )
        return depth_raster

    def make(self, key):

        spikes_data = putils.prepare_spikes_data(key)

        # pick one example trial and generate depth raster
        trials_all = (behavior.TrialSet.Trial & key).proj(
            'trial_response_choice',
            'trial_feedback_type',
            'trial_stim_on_time',
            'trial_feedback_time',
            'trial_start_time',
            'trial_end_time',
            trial_duration='trial_end_time-trial_start_time',
            trial_signed_contrast='trial_stim_contrast_right - trial_stim_contrast_left'
        ) & 'trial_duration < 5' & 'trial_response_choice!="No Go"'

        # choice of clockwise and feedback type is positive
        trials_left_correct = trials_all & 'trial_response_choice="CW"' \
            & 'trial_feedback_type=1'
        trials_right_correct = trials_all & 'trial_response_choice="CCW"' \
            & 'trial_feedback_type=1'
        trials_left_incorrect = trials_all & 'trial_response_choice="CW"' \
            & 'trial_feedback_type=-1'
        trials_right_incorrect = trials_all & 'trial_response_choice="CCW"' \
            & 'trial_feedback_type=-1'

        trials_depthraster = []
        for contrast in tqdm(dj.U('trial_signed_contrast') & trials_all):
            left_correct = (trials_left_correct & contrast).fetch()
            if len(left_correct):
                trial = np.random.choice(left_correct)
                trial_depthraster = self.create_trial_raster(
                    key, spikes_data, trial,
                    'Correct Left Contrast', contrast)
                trials_depthraster.append(trial_depthraster.copy())

            left_incorrect = (trials_left_incorrect & contrast).fetch()
            if len(left_incorrect):
                trial = np.random.choice(left_incorrect)
                trial_depthraster = self.create_trial_raster(
                    key, spikes_data, trial,
                    'Incorrect Left Contrast', contrast)
                trials_depthraster.append(trial_depthraster.copy())

            right_correct = (trials_right_correct & contrast).fetch()
            if len(right_correct):
                trial = np.random.choice(right_correct)
                trial_depthraster = self.create_trial_raster(
                    key, spikes_data, trial,
                    'Correct Right Contrast', contrast)
                trials_depthraster.append(trial_depthraster.copy())

            right_incorrect = (trials_right_incorrect & contrast).fetch()
            if len(right_incorrect):
                trial = np.random.choice(right_incorrect)
                trial_depthraster = self.create_trial_raster(
                    key, spikes_data, trial,
                    'Incorrect Right Contrast', contrast)
                trials_depthraster.append(trial_depthraster.copy())

            try:
                self.insert(trials_depthraster, skip_duplicates=True)
            except Error:
                for trial_dr in trials_depthraster:
                    self.insert1(trial_dr)

            trials_depthraster = []
