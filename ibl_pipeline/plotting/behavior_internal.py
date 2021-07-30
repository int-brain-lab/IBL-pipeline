import datajoint as dj
import inspect
from ..analyses import behavior
from .. import behavior as behavior_ingest
from .. import reference, subject, action, acquisition, data
from . import plotting_utils_behavior as putils
import numpy as np
import pandas as pd
from tqdm import tqdm
from ..utils import psychofit as psy
import plotly
import plotly.graph_objs as go
import statsmodels.stats.proportion as smp
import datetime
import matplotlib.pyplot as plt
import os
from . import behavior_internal

try:
    from oneibl.one import ONE
    one = ONE()
except:
    print('ONE not installed.')

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_plotting_behavior')


@schema
class WaterTypeColor(dj.Computed):
    definition = """
    -> action.WaterType
    ---
    water_type_color:  varchar(32)
    """

    def make(self, key):

        original_water_types = ['Citric Acid Water 2%', 'Hydrogel',
                                'Hydrogel 5% Citric Acid',
                                'Water', 'Water 1% Citric Acid',
                                'Water 10% Sucrose',
                                'Water 15% Sucrose', 'Water 2% Citric Acid']
        original_colors = ['red', 'orange', 'blue', 'rgba(55, 128, 191, 0.7)',
                           'rgba(200, 128, 191, 0.7)',
                           'purple', 'rgba(50, 171, 96, 0.9)', 'red']

        mapping = {
            watertype: color
            for watertype, color in zip(original_water_types, original_colors)}

        if key['watertype_name'] in original_water_types:
            water_type_color = dict(
                **key, water_type_color=mapping[key['watertype_name']])
        else:
            water_type_color = dict(
                **key, water_type_color='rgba({}, {}, {}, 0.7)'.format(
                    np.random.randint(255), np.random.randint(255), np.random.randint(255)))

        self.insert1(water_type_color)


behavior_shared = dj.create_virtual_module('behavior_shared', 'ibl_plotting_behavior')


class WaterWeight(dj.Part):
    master = behavior_shared.CumulativeSummary
    definition = """
    -> master
    ---
    water_weight: longblob    # dict for the plotting info
    """

    def make(self, key, d):
        subj = subject.Subject & key
        # plot for water weight
        water_type_names, water_type_colors = WaterTypeColor.fetch(
            'watertype_name', 'water_type_color')
        water_type_map = dict()

        for watertype, color in zip(water_type_names, water_type_colors):
            water_type_map.update({watertype: color})

        if action.WaterAdministration * action.Weighing & key:
            water_weight_entry = key.copy()
            # get water and date
            water_info_query = (action.WaterAdministration & subj).proj(
                'water_administered', 'watertype_name',
                water_date='DATE(administration_time)')
            water_info = water_info_query.fetch(as_dict=True)
            water_info = pd.DataFrame(water_info)
            water_types = water_info.watertype_name.unique()
            water_info_type = water_info.pivot_table(
                index='water_date', columns='watertype_name',
                values='water_administered', aggfunc='sum')
            max_water_intake = np.nanmax(water_info_type.values) + 0.2
            yrange_water = [0, max_water_intake]
            water_info_type = water_info_type.where(
                (pd.notnull(water_info_type)), None)
            weight_info_query = (action.Weighing & subj).proj(
                'weight', weighing_date='DATE(weighing_time)')
            weight_info = weight_info_query.fetch(as_dict=True)
            weight_info = pd.DataFrame(weight_info)
            weight_info = weight_info.where((pd.notnull(weight_info)), None)

            # get water restriction period
            water_restrictions = (action.WaterRestriction & subj).proj(
                'reference_weight',
                res_start='DATE(restriction_start_time)',
                res_end='DATE(restriction_end_time)')

            data = [
                go.Bar(
                    x=[t.strftime('%Y-%m-%d')
                       for t in water_info_type.index.tolist()],
                    y=water_info_type[water_type].tolist(),
                    marker=dict(color=water_type_map[water_type]),
                    name=water_type,
                    yaxis='y1'
                )
                for water_type in water_types
            ]

            data.append(
                go.Scatter(
                    x=[t.strftime('%Y-%m-%d')
                       for t in weight_info['weighing_date'].tolist()],
                    y=weight_info['weight'].tolist(),
                    mode='lines+markers',
                    name='Weight',
                    marker=dict(
                        size=6,
                        color='black',
                        line=dict(
                            color='white',
                            width=1)
                    ),
                    legendgroup='weight',
                    yaxis='y2'
                ))

            # monday marks
            data = putils.create_monday_plot(data, yrange_water, d['mondays'])

            # water restriction marks and reference weight marks
            for iwater, water_res in \
                    enumerate(water_restrictions.fetch(as_dict=True)):

                if iwater == 0:
                    show_res_legend = True
                else:
                    show_res_legend = False

                res_start = water_res['res_start'].strftime('%Y-%m-%d')

                if water_res['res_end']:
                    res_end = water_res['res_end'].strftime('%Y-%m-%d')
                else:
                    res_end = d['last_date_str']
                data.append(
                    go.Scatter(
                        x=[res_start, res_start],
                        y=yrange_water,
                        mode="lines",
                        line=dict(
                            width=1,
                            color='red',
                        ),
                        name='Water restriction start',
                        yaxis='y1',
                        showlegend=show_res_legend,
                        legendgroup='restriction'
                    )
                )

                if water_res['res_end']:

                    data.append(
                        go.Scatter(
                            x=[res_end, res_end],
                            y=yrange_water,
                            mode="lines",
                            line=dict(
                                width=1,
                                color='darkgreen',
                            ),
                            name='Water restriction end',
                            yaxis='y1',
                            showlegend=show_res_legend,
                            legendgroup='restriction'
                        )
                    )

                data.append(
                    go.Scatter(
                        x=[res_start, res_end],
                        y=[water_res['reference_weight']*0.85,
                           water_res['reference_weight']*0.85],
                        mode="lines",
                        line=dict(
                            width=1,
                            color='orange',
                            dash='dashdot'
                        ),
                        name='85% reference weight',
                        yaxis='y2',
                        showlegend=show_res_legend,
                        legendgroup='weight_ref',
                        hoverinfo='y'
                    )
                )

                data.append(
                    go.Scatter(
                        x=[res_start, res_end],
                        y=[water_res['reference_weight']*0.75,
                           water_res['reference_weight']*0.75],
                        mode="lines",
                        line=dict(
                            width=1,
                            color='red',
                            dash='dashdot'
                        ),
                        name='75% reference weight',
                        yaxis='y2',
                        showlegend=show_res_legend,
                        legendgroup='weight_ref',
                        hoverinfo='y'
                    )
                )

            layout = go.Layout(
                yaxis=dict(
                    title='Water intake (mL)',
                    range=yrange_water
                ),
                yaxis2=dict(
                    title='Weight (g)',
                    overlaying='y',
                    side='right',
                ),
                width=1000,
                height=500,
                title=dict(
                    text='Water intake and weight',
                    x=0.3,
                    y=0.9
                ),
                xaxis=dict(
                    title='Date',
                    range=[d['first_date_str'], d['last_date_str']]
                ),
                legend=dict(
                    x=1.1,
                    y=0.9,
                    orientation='v'),
                barmode='stack',
                template=dict(
                    layout=dict(
                        plot_bgcolor="white"
                    )
                )
            )
            fig = go.Figure(data=data, layout=layout)
            water_weight_entry['water_weight'] = fig.to_plotly_json()
            print('inserting water weight ...')
            self.insert1(water_weight_entry)


# Manually decorate WaterWeight table class.
context = dict(
    inspect.currentframe().f_locals,
    master=behavior_shared.CumulativeSummary,
    self=WaterWeight,
    CumulativeSummary=behavior_shared.CumulativeSummary)

if '0.12' in dj.__version__:
    schema.process_table_class(WaterWeight, context=context)
elif '0.13' in dj.__version__:
    schema._decorate_table(WaterWeight, context=context)
else:
    raise NotImplementedError('Cannot declare WaterWeight table without DataJoint 0.12 or 0.13.')


ingested_sessions = acquisition.Session & 'task_protocol is not NULL' \
    & behavior_ingest.TrialSet
subjects_alive = (subject.Subject - subject.Death) & 'sex != "U"' \
    & action.Weighing & action.WaterAdministration & ingested_sessions


@schema
class DailyLabSummary(dj.Computed):
    definition = """
    -> reference.Lab
    last_session_time:      datetime        # last date of session
    """

    sessions_lab = acquisition.Session * subjects_alive * subject.SubjectLab \
        * behavior.SessionTrainingStatus
    key_source = dj.U('lab_name', 'last_session_time') & reference.Lab.aggr(
        sessions_lab, last_session_time='MAX(session_start_time)')

    def make(self, key):

        self.insert1(key)
        subjects = subjects_alive * subject.SubjectLab & key

        last_sessions = subjects.aggr(
            ingested_sessions * behavior.SessionTrainingStatus,
            'subject_nickname', session_start_time='max(session_start_time)')
        last_sessions = last_sessions * acquisition.Session * \
            behavior.SessionTrainingStatus

        filerecord = data.FileRecord & subjects.fetch('KEY') & 'relative_path LIKE "%alf%"'
        last_filerecord = subjects.aggr(
            filerecord, latest_session_on_flatiron='max(session_start_time)')

        summary = (last_sessions*last_filerecord).proj(
            'subject_nickname', 'task_protocol', 'training_status',
            'latest_session_on_flatiron').fetch(
                as_dict=True)

        for entry in summary:
            subj = subject.Subject & entry
            protocol = entry['task_protocol'].partition('ChoiseWorld')[0]

            # --- check for data availability ---

            # last session_start_time in table acquisition.Session
            if not len(acquisition.Session & subj):
                data_update_status = 'No behavioral data collected'
            else:
                # get the latest session query
                last_session = subj.aggr(
                    acquisition.Session,
                    session_start_time='max(session_start_time)')

                last_session_date = last_session.proj(
                    session_date='date(session_start_time)')

                last_date = last_session_date.fetch1(
                    'session_date').strftime('%Y-%m-%d')

                # existence of CompleteTrialSet tuple for latest session
                if not len(behavior_ingest.CompleteTrialSession & last_session):
                    data_update_status = """
                    Data in the last session on {} were not uploaded
                    or partially uploaded to FlatIron.
                    """.format(last_date)
                elif not len(behavior_ingest.TrialSet & last_session):
                    data_update_status = """
                    Ingest error in TrialSet for data on {}.
                    """.format(last_date)
                elif not len(behavior.BehavioralSummaryByDate & last_session_date):
                    data_update_status = """
                    Ingest error in BehavioralSummaryByDate for
                    data on {}
                    """.format(last_date)
                elif not len(behavior_shared.CumulativeSummary & last_session.proj(latest_session='session_date')):
                    data_update_status = """
                    Error in creating cumulative plots for data on {}
                    """.format(last_date)
                else:
                    data_update_status = """
                    Data up to date
                    """.format(last_date)

            subject_summary = dict(
                **key,
                subject_uuid=entry['subject_uuid'],
                subject_nickname=entry['subject_nickname'],
                latest_session_ingested=entry['session_start_time'],
                latest_session_on_flatiron=entry['latest_session_on_flatiron'],
                latest_task_protocol=entry['task_protocol'],
                latest_training_status=entry['training_status'],
                n_sessions_current_protocol=len(
                    ingested_sessions & subj &
                    'task_protocol LIKE "{}%"'.format(protocol)),
                data_update_status=data_update_status
            )
            self.SubjectSummary.insert1(subject_summary)

    class SubjectSummary(dj.Part):
        definition = """
        -> master
        subject_uuid:                uuid
        ---
        subject_nickname:            varchar(64)
        latest_session_ingested:     datetime
        latest_session_on_flatiron:  datetime
        latest_task_protocol:        varchar(128)
        latest_training_status:      varchar(64)
        n_sessions_current_protocol: int
        data_update_status:          varchar(255)
        subject_summary_ts=CURRENT_TIMESTAMP:      timestamp
        """

    @classmethod
    def detect_dead_subjects_from_alyx(cls, insert_into_death_table=False):
        """Helper function to detect all dead subjects that are still in SubjectSummary

        Args:
            insert_into_death_table (boolean): whether insert the entries into the Death table

        Returns:
            (list of uuids): list of uuids for dead animals
        """

        dead_subj_uuids = []
        for subj in tqdm(cls.SubjectSummary.fetch('KEY')):

            dead_subj = one.alyx.rest('subjects', 'list', id=str(subj['subject_uuid']), alive=False)
            if dead_subj:
                dead_subj_uuids.append(subj['subject_uuid'])
                if insert_into_death_table:
                    subject.Death.insert1(dict(subject_uuid=subj['subject_uuid'],
                                               death_date=dead_subj[0]['death_date']),
                                          skip_duplicates=True)

        return dead_subj_uuids
