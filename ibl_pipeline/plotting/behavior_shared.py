import datetime
import os

import datajoint as dj
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import statsmodels.stats.proportion as smp

from ibl_pipeline import acquisition, action
from ibl_pipeline import behavior as behavior_ingest
from ibl_pipeline import mode, reference, subject
from ibl_pipeline.analyses import behavior
from ibl_pipeline.plotting import plotting_utils_behavior as putils
from ibl_pipeline.utils import psychofit as psy

schema = dj.schema(dj.config.get("database.prefix", "") + "ibl_plotting_behavior")


@schema
class SessionPsychCurve(dj.Computed):
    definition = """
    -> behavior.PsychResults
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    fit_pars:       longblob     # dictionary list for fit parameters
    """
    key_source = behavior.PsychResults & behavior.PsychResultsBlock.proj()

    def make(self, key):

        sessions = behavior.PsychResultsBlock & key
        fig = putils.create_psych_curve_plot(sessions)
        key["plotting_data"] = fig.to_plotly_json()
        key["fit_pars"] = putils.get_fit_pars(sessions)
        self.insert1(key)


@schema
class SessionReactionTimeContrast(dj.Computed):
    definition = """
    -> behavior_ingest.TrialSet
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """
    key_source = behavior_ingest.TrialSet & behavior.ReactionTimeContrastBlock

    def make(self, key):
        sessions = behavior.PsychResultsBlock * behavior.ReactionTimeContrastBlock & key
        fig = putils.create_rt_contrast_plot(sessions)
        key["plotting_data"] = fig.to_plotly_json()
        self.insert1(key)


@schema
class SessionReactionTimeTrialNumber(dj.Computed):
    definition = """
    -> behavior_ingest.TrialSet
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """

    key_source = behavior_ingest.TrialSet & (
        behavior_ingest.CompleteTrialSession
        & 'stim_on_times_status in ("Complete", "Partial") or \
             go_cue_trigger_times_status in ("Complete", "Partial")'
    )

    def make(self, key):
        # get all trial of the session
        trials = (
            behavior_ingest.TrialSet.Trial
            & key
            & "trial_stim_on_time is not NULL or \
             trial_go_cue_trigger_time is not NULL"
        )

        fig = putils.create_rt_trialnum_plot(trials)
        key["plotting_data"] = fig.to_plotly_json()
        self.insert1(key)


@schema
class DatePsychCurve(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    fit_pars:       longblob     # dictionary list for fit parameters
    """

    def make(self, key):

        sessions = behavior.BehavioralSummaryByDate.PsychResults & key
        fig = putils.create_psych_curve_plot(sessions)
        key["plotting_data"] = fig.to_plotly_json()
        key["fit_pars"] = putils.get_fit_pars(sessions)
        self.insert1(key)


@schema
class DateReactionTimeContrast(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob     # dictionary for the plotting info
    """
    key_source = (
        behavior.BehavioralSummaryByDate
        & behavior.BehavioralSummaryByDate.ReactionTimeContrast
    )

    def make(self, key):
        sessions = (
            behavior.BehavioralSummaryByDate.PsychResults
            * behavior.BehavioralSummaryByDate.ReactionTimeContrast
            & key
        )
        fig = putils.create_rt_contrast_plot(sessions)
        key["plotting_data"] = fig.to_plotly_json()
        self.insert1(key)


@schema
class DateReactionTimeTrialNumber(dj.Computed):
    definition = """
    -> behavior.BehavioralSummaryByDate
    ---
    plotting_data:  longblob   # dictionary for the plotting info
    """

    def make(self, key):
        trial_sets = (
            behavior_ingest.TrialSet
            & (
                behavior_ingest.CompleteTrialSession
                & 'stim_on_times_status in ("Complete", "Partial") or \
                        go_cue_trigger_times_status in ("Complete", "Partial")'
            )
        ).proj(session_date="DATE(session_start_time)")
        trials = behavior_ingest.TrialSet.Trial & (
            behavior_ingest.TrialSet * trial_sets & key
        )

        if not len(trials):
            return

        fig = putils.create_rt_trialnum_plot(trials)
        key["plotting_data"] = fig.to_plotly_json()
        self.insert1(key)


@schema
class LatestDate(dj.Manual):
    # compute the last date of any event for individual subjects
    # (no longer needed for the new ingestion)
    definition = """
    -> subject.Subject
    checking_ts=CURRENT_TIMESTAMP: timestamp
    ---
    latest_date: date
    """


@schema
class SubjectLatestEvent(dj.Manual):
    definition = """  # Event and time information of the latest event for a particular subject
    -> subject.Subject
    latest_event_time: datetime
    ---
    checking_ts=CURRENT_TIMESTAMP: timestamp
    """

    @classmethod
    def create_entry(cls, subject_key):
        latest_behavior, latest_water_weight = None, None

        if behavior.BehavioralSummaryByDate & subject_key:
            latest_behavior = (
                subject.Subject & behavior.BehavioralSummaryByDate & subject_key
            ).aggr(acquisition.Session, last_behavior_time="MAX(session_start_time)")

        if mode != "public":
            water_weight = action.Weighing * action.WaterAdministration & subject_key
            if water_weight:
                latest_weight = subject.Subject.aggr(
                    action.Weighing & subject_key,
                    last_weighing_time="MAX(weighing_time)",
                )
                latest_water = subject.Subject.aggr(
                    action.WaterAdministration & subject_key,
                    last_water_time="MAX(administration_time)",
                )
                latest_water_weight = (latest_water * latest_weight).proj(
                    last_water_weight_time="GREATEST(last_water_time, last_weighing_time)"
                )

        if latest_behavior and latest_water_weight:
            last_behavior_date = latest_behavior.fetch1("last_behavior_time")
            last_water_weight_date = latest_water_weight.fetch1(
                "last_water_weight_time"
            )
            latest_time = max([last_behavior_date, last_water_weight_date])
        elif latest_behavior:
            latest_time = latest_behavior.fetch1("last_behavior_time")
        elif latest_water_weight:
            latest_time = latest_water_weight.fetch1("last_water_weight_time")
        else:
            return

        key = {**subject_key, "latest_event_time": latest_time}
        if key in cls.proj():
            return

        cls.insert1(key)

        # also keeping LatestDate in sync
        # - for legacy reason, to be removed if LatestDate is no longer used
        LatestDate.insert1({**subject_key, "latest_date": latest_time.date()})


@schema
class SubjectLatestDate(dj.Lookup):
    # This table is only used by Navigator for fast fetching
    definition = """
    -> subject.Subject
    ---
    latest_date: date
    """


@schema
class CumulativeSummary(dj.Computed):
    # This table contains four plots of the cumulative summary
    definition = """
    -> subject.Subject
    latest_date: date      # last date of any event for the subject
    ---
    cumulative_summary_ts=null : timestamp
    latest_time=null: datetime  # last datetime of any event for the subject
    session_count=null: int     # total number of sessions for the subject at this time of calculation
    """

    @property
    def key_source(self):
        """
        Subject and "latest_date", where "latest_date" is the most recent date
         found in "SubjectLatestEvent" for a particular subject
        """
        latest = subject.Subject.aggr(
            SubjectLatestEvent, latest_event_time="MAX(latest_event_time)"
        )
        return latest.proj(latest_date="DATE(latest_event_time)")

    @classmethod
    def get_outdated_entries(cls):
        outdated_events = (
            cls
            & (
                cls * SubjectLatestEvent
                & cls.key_source
                & ["latest_time IS NULL", "latest_event_time != latest_time"]
            ).proj()
        )
        outdated_sessions = (
            cls
            & (
                (cls * SubjectLatestEvent & cls.key_source).aggr(
                    behavior_ingest.TrialSet,
                    "session_count",
                    latest_session_count="count(session_start_time)",
                    keep_all_rows=True,
                )
                & ["session_count IS NULL", "latest_session_count != session_count"]
            ).proj()
        )
        return outdated_events.proj() + outdated_sessions.proj()

    class TrialCountsSessionDuration(dj.Part):
        definition = """
        -> master
        ---
        trial_counts_session_duration: longblob    # dict for the plotting info
        """

    class PerformanceReactionTime(dj.Part):
        definition = """
        -> master
        ---
        performance_reaction_time: longblob    # dict for the plotting info
        """

    class ContrastHeatmap(dj.Part):
        definition = """
        -> master
        ---
        contrast_heatmap: longblob    # dict for the plotting info
        """

    class FitPars(dj.Part):
        definition = """
        -> master
        ---
        fit_pars: longblob  # dict for the plotting info
        """

    def make(self, key):
        latest_time = (
            (subject.Subject & key)
            .aggr(SubjectLatestEvent, latest_event_time="MAX(latest_event_time)")
            .fetch1("latest_event_time")
        )

        key["latest_date"] = latest_time.date()
        self.insert1(
            {
                **key,
                "latest_time": latest_time,
                "session_count": len(behavior_ingest.TrialSet & key),
            }
        )

        # check the environment, public or internal
        public = mode == "public"

        subj = subject.Subject & key
        # get the first date when animal became "trained" and "ready for ephys"
        status = putils.get_status(subj)
        # get date range and mondays
        d = putils.get_date_range(subj, include_water_weight=not public)

        if d["seven_months_date"]:
            status["is_over_seven_months"] = True
            status["seven_months_date"] = d["seven_months_date"]
        else:
            status["is_over_seven_months"] = False

        # plot for trial counts and session duration
        if behavior_ingest.TrialSet & key:
            trial_cnts = key.copy()
            # get trial counts and session length to date
            session_info = (
                (behavior_ingest.TrialSet * acquisition.Session & subj)
                .proj(
                    "n_trials",
                    session_date="DATE(session_start_time)",
                    session_duration="TIMESTAMPDIFF(MINUTE, \
                    session_start_time, session_end_time)",
                )
                .fetch(as_dict=True)
            )
            session_info = pd.DataFrame(session_info)
            session_info = session_info.where((pd.notnull(session_info)), None)

            n_trials = session_info["n_trials"].tolist()
            max_trials = max(n_trials)
            yrange = [0, max_trials + 50]

            trial_counts = go.Scatter(
                x=[
                    t.strftime("%Y-%m-%d")
                    for t in session_info["session_date"].tolist()
                ],
                y=session_info["n_trials"].tolist(),
                mode="markers+lines",
                marker=dict(size=6, color="black", line=dict(color="white", width=1)),
                name="trial counts",
                yaxis="y1",
                showlegend=False,
            )

            session_length = go.Scatter(
                x=[
                    t.strftime("%Y-%m-%d")
                    for t in session_info["session_date"].tolist()
                ],
                y=session_info["session_duration"].tolist(),
                mode="markers+lines",
                marker=dict(size=6, color="red", line=dict(color="white", width=1)),
                name="session duration",
                yaxis="y2",
                showlegend=False,
            )

            data = [trial_counts, session_length]

            # add monday plots
            data = putils.create_monday_plot(data, yrange, d["mondays"])

            # add ephys dates and good enough markers
            if d["ephys_dates"]:
                data = putils.create_good_enough_brainmap_plot(
                    data, yrange, d["ephys_dates"], d["good_enough"]
                )

            # add status plots
            data = putils.create_status_plot(data, yrange, status, public=public)

            layout = go.Layout(
                yaxis=dict(title="Trial counts", range=yrange),
                yaxis2=dict(
                    title="Session duration (mins)",
                    overlaying="y",
                    color="red",
                    side="right",
                ),
                xaxis=dict(
                    title="Date",
                    range=[d["first_date_str"], d["last_date_str"]],
                    showgrid=False,
                ),
                width=700,
                height=400,
                title=dict(text="Trial counts and session duration", x=0.18, y=0.85),
                legend=dict(x=1.2, y=0.8, orientation="v"),
                template=dict(layout=dict(plot_bgcolor="white")),
            )

            fig = go.Figure(data=data, layout=layout)
            trial_cnts["trial_counts_session_duration"] = fig.to_plotly_json()
            self.TrialCountsSessionDuration.insert1(trial_cnts)

        # plot for performance reaction time and fit pars
        if behavior.BehavioralSummaryByDate & key:
            perf_rt = key.copy()
            session_info = (
                (
                    behavior.BehavioralSummaryByDate
                    * behavior.BehavioralSummaryByDate.ReactionTimeByDate
                    & key
                )
                .proj("session_date", "performance_easy", "median_reaction_time")
                .fetch(as_dict=True)
            )
            session_info = pd.DataFrame(session_info)
            yrange = [0, 1.1]
            perf_easy = [
                None if not p or np.isnan(p) else p
                for p in session_info["performance_easy"]
            ]

            median_rt = [
                None if not p or np.isnan(p) else p
                for p in session_info["median_reaction_time"]
            ]

            performance_easy = go.Scatter(
                x=[
                    t.strftime("%Y-%m-%d")
                    for t in session_info["session_date"].tolist()
                ],
                y=perf_easy,
                mode="markers+lines",
                marker=dict(size=6, color="black", line=dict(color="white", width=1)),
                name="performance easy",
                yaxis="y1",
                showlegend=False,
            )
            rt = go.Scatter(
                x=[
                    t.strftime("%Y-%m-%d")
                    for t in session_info["session_date"].tolist()
                ],
                y=median_rt,
                mode="markers+lines",
                marker=dict(size=6, color="red", line=dict(color="white", width=1)),
                name="reaction time",
                yaxis="y2",
                showlegend=False,
            )

            data = [performance_easy, rt]

            # add monday plots
            data = putils.create_monday_plot(data, yrange, d["mondays"])

            # add good enough for brain map plot
            if d["ephys_dates"]:
                data = putils.create_good_enough_brainmap_plot(
                    data, yrange, d["ephys_dates"], d["good_enough"]
                )

            # add status plots
            data = putils.create_status_plot(data, yrange, status, public=public)

            layout = go.Layout(
                yaxis=dict(title="Performance on easy trials", range=yrange),
                yaxis2=dict(
                    title="Median reaction time (s)",
                    overlaying="y",
                    color="red",
                    side="right",
                    type="log",
                    range=np.log10([0.1, 10]).tolist(),
                    dtick=np.log10([0.1, 1, 10]).tolist(),
                ),
                xaxis=dict(title="Date", showgrid=False),
                width=700,
                height=400,
                title=dict(text="Performance and median reaction time", x=0.14, y=0.85),
                legend=dict(x=1.2, y=0.8, orientation="v"),
                template=dict(layout=dict(plot_bgcolor="white")),
            )

            fig = go.Figure(data=data, layout=layout)
            perf_rt["performance_reaction_time"] = fig.to_plotly_json()
            self.PerformanceReactionTime.insert1(perf_rt)

            # plot for fit parameter changes over time
            # get trial counts and session length to date
            fit_pars_entry = key.copy()
            fit_pars = (
                (behavior.BehavioralSummaryByDate.PsychResults & key)
                .proj(
                    "session_date",
                    "prob_left",
                    "threshold",
                    "bias",
                    "lapse_low",
                    "lapse_high",
                )
                .fetch(as_dict=True)
            )
            fit_pars = pd.DataFrame(fit_pars)
            par_names = ["threshold", "bias", "lapse_low", "lapse_high"]
            thresholds = [[19, 19], [16, 16, -16, -16], [0.2, 0.2], [0.2, 0.2]]
            xranges = [
                [d["first_date_str"], d["last_date_str"]],
                [
                    d["first_date_str"],
                    d["last_date_str"],
                    d["last_date_str"],
                    d["first_date_str"],
                ],
                [d["first_date_str"], d["last_date_str"]],
                [d["first_date_str"], d["last_date_str"]],
            ]
            yranges = [[0, 100], [-100, 100], [0, 1], [0, 1]]

            pars = dict()
            for par_name in par_names:
                pars[par_name] = []

            prob_lefts = fit_pars["prob_left"].unique()

            for iprob_left, prob_left in enumerate(prob_lefts):
                prob_left_filter = fit_pars["prob_left"] == prob_left
                dot_color, error_color = putils.get_color(prob_left)

                fit_pars_sub = fit_pars[prob_left_filter]

                for ipar, par_name in enumerate(par_names):
                    if ipar == 0:
                        show_legend = True
                    else:
                        show_legend = False
                    pars[par_name].append(
                        go.Scatter(
                            x=[
                                t.strftime("%Y-%m-%d")
                                for t in fit_pars_sub["session_date"].tolist()
                            ],
                            y=fit_pars_sub[par_name].tolist(),
                            mode="markers",
                            marker=dict(size=5, color=dot_color, opacity=0.8),
                            name=f"p_left = {prob_left}",
                            xaxis="x{}".format(4 - ipar),
                            yaxis="y{}".format(4 - ipar),
                            showlegend=show_legend,
                            legendgroup="p_left",
                        )
                    )

            pars_data = [
                pars[par_name][i]
                for i, prob_left in enumerate(prob_lefts)
                for par_name in par_names
            ]

            for ipar, par_name in enumerate(par_names):
                if ipar == 0:
                    show_legend = True
                else:
                    show_legend = False

                pars_data.append(
                    go.Scatter(
                        x=xranges[ipar],
                        y=thresholds[ipar],
                        mode="lines",
                        line=dict(width=1, color="darkgreen", dash="dashdot"),
                        name="threshold for trained",
                        xaxis="x{}".format(4 - ipar),
                        yaxis="y{}".format(4 - ipar),
                        showlegend=show_legend,
                        legendgroup="date",
                    )
                )

                # add monday plots
                pars_data = putils.create_monday_plot(
                    pars_data,
                    yranges[ipar],
                    d["mondays"],
                    xaxis="x{}".format(4 - ipar),
                    yaxis="y{}".format(4 - ipar),
                    show_legend_external=show_legend,
                )

                # add good enough for brainmap plots
                if d["ephys_dates"]:
                    pars_data = putils.create_good_enough_brainmap_plot(
                        pars_data,
                        yranges[ipar],
                        d["ephys_dates"],
                        d["good_enough"],
                        xaxis="x{}".format(4 - ipar),
                        yaxis="y{}".format(4 - ipar),
                        show_legend_external=show_legend,
                    )

                # add status plots
                pars_data = putils.create_status_plot(
                    pars_data,
                    yranges[ipar],
                    status,
                    xaxis="x{}".format(4 - ipar),
                    yaxis="y{}".format(4 - ipar),
                    show_legend_external=show_legend,
                    public=public,
                )

            x_axis_range = [
                d["first_date_str"],
                (d["last_date"] - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            ]
            layout = go.Layout(
                xaxis1=dict(
                    domain=[0, 1], range=x_axis_range, title="Date", showgrid=False
                ),
                yaxis1=dict(
                    domain=[0, 0.2],
                    anchor="x1",
                    showgrid=False,
                    range=[-0.02, 1.02],
                    title="$Lapse high\ (\\lambda)$",
                ),
                xaxis2=dict(domain=[0, 1], range=x_axis_range, showgrid=False),
                yaxis2=dict(
                    domain=[0.25, 0.45],
                    anchor="x2",
                    showgrid=False,
                    range=[-0.02, 1.02],
                    title="$Lapse low\ (\\gamma)$",
                ),
                xaxis3=dict(domain=[0, 1], range=x_axis_range, showgrid=False),
                yaxis3=dict(
                    domain=[0.5, 0.7],
                    anchor="x3",
                    showgrid=False,
                    range=[-105, 105],
                    title="$Bias\ (\\mu)$",
                ),
                xaxis4=dict(domain=[0, 1], range=x_axis_range, showgrid=False),
                yaxis4=dict(
                    domain=[0.75, 1],
                    anchor="x4",
                    showgrid=False,
                    range=[-5, 105],
                    title="$Threshold\ (\\sigma)$",
                ),
                height=1000,
                width=600,
                title=dict(text="Fit Parameters", x=0.3, y=0.93),
                legend=dict(x=1.1, y=1, orientation="v"),
                template=dict(layout=dict(plot_bgcolor="white")),
            )

            fig = go.Figure(data=pars_data, layout=layout)
            fit_pars_entry["fit_pars"] = fig.to_plotly_json()
            self.FitPars.insert1(fit_pars_entry)

        # plot for contrast heatmap
        if (
            behavior.BehavioralSummaryByDate.PsychResults
            & key
            & "ABS(prob_left-0.5)<0.001"
        ):
            con_hm = key.copy()
            # get trial counts and session length to date
            sessions = (
                behavior.BehavioralSummaryByDate.PsychResults & "prob_left=0.5" & key
            ).proj("session_date", "signed_contrasts", "prob_choose_right")

            # get date ranges and mondays
            d = putils.get_date_range(subj, include_water_weight=not public)

            # get contrast and p_prob_choose_right per day
            contrast_list = []
            for day in d["date_array"]:
                if sessions & {"session_date": day}:
                    session = (sessions & {"session_date": day}).fetch(as_dict=True)
                    session = session[0]
                    for icontrast, contrast in enumerate(session["signed_contrasts"]):
                        contrast_list.append(
                            {
                                "session_date": session["session_date"],
                                "signed_contrast": round(contrast, 2) * 100,
                                "prob_choose_right": session["prob_choose_right"][
                                    icontrast
                                ],
                            }
                        )
                else:
                    contrast_list.append(
                        {
                            "session_date": day,
                            "signed_contrast": 100,
                            "prob_choose_right": np.nan,
                        }
                    )

            contrast_df = pd.DataFrame(contrast_list)
            contrast_map = contrast_df.pivot(
                "signed_contrast", "session_date", "prob_choose_right"
            ).sort_values(by="signed_contrast", ascending=False)

            contrast_map = contrast_map.where(pd.notnull(contrast_map), None)
            contrasts = np.sort(contrast_df["signed_contrast"].unique())

            data = [
                dict(
                    x=[t.strftime("%Y-%m-%d") for t in contrast_map.columns.tolist()],
                    y=list(range(len(contrast_map.index.tolist())))[::-1],
                    z=contrast_map.values.tolist(),
                    zmax=1,
                    zmin=0,
                    xgap=1,
                    ygap=1,
                    type="heatmap",
                    colorbar=dict(
                        thickness=10,
                        title="Rightward Choice (%)",
                        titleside="right",
                    ),
                    colorscale="PuOr",
                )
            ]

            data = putils.create_monday_plot(data, [-100, 100], d["mondays"])

            layout = go.Layout(
                xaxis=dict(title="Date", showgrid=False),
                yaxis=dict(
                    title="Contrast (%)",
                    range=[0, len(contrast_map.index.tolist())],
                    tickmode="array",
                    tickvals=list(range(0, len(contrast_map.index.tolist()))),
                    ticktext=[str(contrast) for contrast in contrasts],
                ),
                width=700,
                height=400,
                title=dict(text="Contrast heatmap", x=0.3, y=0.85),
                legend=dict(x=1.2, y=0.8, orientation="v"),
                template=dict(layout=dict(plot_bgcolor="white")),
            )

            fig = go.Figure(data=data, layout=layout)
            con_hm["contrast_heatmap"] = fig.to_plotly_json()
            self.ContrastHeatmap.insert1(con_hm)

        if mode != "public":
            from ibl_pipeline.plotting.behavior_internal import WaterWeight

            self.WaterWeight = WaterWeight
            self.WaterWeight().make(key, d)
