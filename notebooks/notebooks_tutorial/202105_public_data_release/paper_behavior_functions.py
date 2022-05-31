# -*- coding: utf-8 -*-
"""
General functions and queries for the analysis of behavioral data from the IBL task
Guido Meijer, Anne Urai, Alejandro Pan Vazquez & Miles Wells
16 Jan 2020
"""
import os
import warnings
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

import brainbox.behavior.pyschofit as psy
import datajoint as dj
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Supress seaborn future warnings
warnings.simplefilter(action="ignore", category=FutureWarning)

# Some constants
URL = "http://ibl.flatironinstitute.org/public/behavior_paper_data.zip"
QUERY = True  # Whether to query data through DataJoint (True) or use downloaded csv files (False)
EXAMPLE_MOUSE = "KS014"  # Mouse nickname used as an example
CUTOFF_DATE = (
    "2020-03-23"  # Date after which sessions are excluded, previously 30th Nov
)
STABLE_HW_DATE = "2019-06-10"  # Date after which hardware was deemed stable

# LAYOUT
FIGURE_HEIGHT = 2  # inch
FIGURE_WIDTH = 8  # inch

# EXCLUDED SESSIONS
EXCLUDED_SESSIONS = ["a9fb578a-9d7d-42b4-8dbc-3b419ce9f424"]  # Session UUID


def group_colors():
    return sns.color_palette("Dark2", 7)


def institution_map():
    institution_map = {
        "UCL": "Lab 1",
        "CCU": "Lab 2",
        "CSHL": "Lab 3",
        "NYU": "Lab 4",
        "Princeton": "Lab 5",
        "SWC": "Lab 6",
        "Berkeley": "Lab 7",
    }
    col_names = [
        "Lab 1",
        "Lab 2",
        "Lab 3",
        "Lab 4",
        "Lab 5",
        "Lab 6",
        "Lab 7",
        "All labs",
    ]

    return institution_map, col_names


def seaborn_style():
    """
    Set seaborn style for plotting figures
    """
    sns.set(
        style="ticks",
        context="paper",
        font="Arial",
        rc={
            "font.size": 9,
            "axes.titlesize": 9,
            "axes.labelsize": 9,
            "lines.linewidth": 1,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "savefig.transparent": True,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "xtick.minor.size": 2,
            "ytick.minor.size": 2,
        },
    )
    matplotlib.rcParams["pdf.fonttype"] = 42
    matplotlib.rcParams["ps.fonttype"] = 42


def figpath():
    # Retrieve absolute path of paper-behavior dir
    repo_dir = os.path.dirname(os.path.realpath(__file__))
    # Make figure directory
    fig_dir = os.path.join(repo_dir, "exported_figs")
    # If doesn't already exist, create
    if not os.path.exists(fig_dir):
        os.mkdir(fig_dir)
    return fig_dir


def datapath():
    """
    Return the location of data directory
    """
    # Retrieve absolute path of paper-behavior dir
    repo_dir = os.path.dirname(os.path.realpath(__file__))
    # Make figure directory
    data_dir = os.path.join(repo_dir, "data")
    # If doesn't already exist, create
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    return data_dir


def load_csv(*args, **kwargs):
    """Loads CSV and pickle data either locally or remotely
    If the input file is not found in the data directory the file is downloaded from a remote
    http server and returned as a pandas DataFrame.
    """
    repo_dir = os.path.dirname(os.path.realpath(__file__))
    local = os.path.join(repo_dir, "data", *args)
    if not os.path.exists(local):
        resp = urlopen(URL)
        zipfile = ZipFile(BytesIO(resp.read()))
        files = zipfile.namelist()
        if not any(x.endswith(args[-1]) for x in files):
            raise FileNotFoundError(f"{args[-1]} not found in {URL}")
        local = zipfile.extract("/".join(("data", *args)), repo_dir)
    loader = pd.read_pickle if local.endswith(".pkl") else pd.read_csv
    return loader(local, **kwargs)


def query_subjects(as_dataframe=False, from_list=False, criterion="trained"):
    """
    Query all mice for analysis of behavioral data
    Parameters
    ----------
    as_dataframe:    boolean if true returns a pandas dataframe (default is False)
    from_list:       loads files from list uuids (array of uuids objects)
    criterion:       what criterion by the 30th of November - trained (a and b), biased, ephys
                     (includes ready4ephysrig, ready4delay and ready4recording).  If None,
                     all mice that completed a training session are returned, with date_trained
                     being the date of their first training session.
    """
    from ibl_pipeline import acquisition, reference, subject
    from ibl_pipeline.analyses import behavior as behavior_analysis

    # Query all subjects with project ibl_neuropixel_brainwide_01 and get the date at which
    # they reached a given training status
    all_subjects = (
        subject.Subject * subject.SubjectLab * reference.Lab * subject.SubjectProject
        & 'subject_project = "ibl_neuropixel_brainwide_01"'
    )
    sessions = acquisition.Session * behavior_analysis.SessionTrainingStatus()
    fields = ("subject_nickname", "sex", "subject_birth_date", "institution_short")

    if criterion is None:
        # Find first session of all mice; date_trained = date of first training session
        subj_query = all_subjects.aggr(
            sessions, *fields, date_trained="min(date(session_start_time))"
        )
    else:  # date_trained = date of first session when criterion was reached
        if criterion == "trained":
            restriction = 'training_status="trained_1a" OR training_status="trained_1b"'
        elif criterion == "biased":
            restriction = 'task_protocol LIKE "%biased%"'
        elif criterion == "ephys":
            restriction = 'training_status LIKE "ready%"'
        else:
            raise ValueError('criterion must be "trained", "biased" or "ephys"')
        subj_query = all_subjects.aggr(
            sessions & restriction,
            *fields,
            date_trained="min(date(session_start_time))",
        )

    if from_list is True:
        data_path = os.path.join(datapath(), "uuids_trained.npy")
        ids = np.load(data_path, allow_pickle=True)
        subj_query = subj_query & [{"subject_uuid": u_id} for u_id in ids]

    # Select subjects that reached criterion before cutoff date
    subjects = subj_query & 'date_trained <= "%s"' % CUTOFF_DATE
    if as_dataframe is True:
        subjects = subjects.fetch(format="frame")
        subjects = subjects.sort_values(by=["lab_name"]).reset_index()

    return subjects


def query_sessions(
    task="all", stable=False, as_dataframe=False, force_cutoff=False, criterion="biased"
):
    """
    Query all sessions for analysis of behavioral data
    Parameters
    ----------
    task:            string indicating sessions of which task to return, can be trianing or biased
                     default is all
    stable:          boolean if True only return sessions with stable hardware, which means
                     sessions after particular date (default is False)
    as_dataframe:    boolean if True returns a pandas dataframe (default is False)
    force_cutoff:    whether the animal had to reach the criterion by the 30th of Nov. Only
                     applies to biased and ready for ephys criterion
    criterion:       what criterion by the 30th of November - trained (includes
                     a and b), biased, ready (includes ready4ephysrig, ready4delay and
                     ready4recording)
    """

    from ibl_pipeline import acquisition

    # Query sessions
    if force_cutoff is True:
        use_subjects = query_subjects(criterion=criterion).proj("subject_uuid")
    else:
        use_subjects = query_subjects().proj("subject_uuid")

    # Query all sessions or only training or biased if required
    if task == "all":
        sessions = (
            acquisition.Session * use_subjects
            & 'task_protocol NOT LIKE "%habituation%"'
        )
    elif task == "training":
        sessions = (
            acquisition.Session * use_subjects & 'task_protocol LIKE "%training%"'
        )
    elif task == "biased":
        sessions = acquisition.Session * use_subjects & 'task_protocol LIKE "%biased%"'
    elif task == "ephys":
        sessions = acquisition.Session * use_subjects & 'task_protocol LIKE "%ephys%"'
    else:
        raise ValueError('task must be "all", "training", "biased" or "ephys"')

    # Only use sessions up until the end of December
    sessions = sessions & 'date(session_start_time) <= "%s"' % CUTOFF_DATE

    # Exclude weird sessions
    sessions = sessions & dj.Not([{"session_uuid": u_id} for u_id in EXCLUDED_SESSIONS])

    # If required only output sessions with stable hardware
    if stable is True:
        sessions = sessions & 'date(session_start_time) > "%s"' % STABLE_HW_DATE

    # Transform into pandas Dataframe if requested
    if as_dataframe is True:
        sessions = sessions.fetch(
            order_by="institution_short, subject_nickname, session_start_time",
            format="frame",
        )
        sessions = sessions.reset_index()

    return sessions


def query_sessions_around_criterion(
    criterion="trained",
    days_from_criterion=(2, 0),
    as_dataframe=False,
    force_cutoff=False,
):
    """
    Query all sessions for analysis of behavioral data
    Parameters
    ----------
    criterion:              string indicating which criterion to use: trained, biased or ephys
    days_from_criterion:    two-element array which indicates which training days around the day
                            the mouse reached criterium to return, e.g. [3, 2] returns three days
                            before criterium reached up until 2 days after (default: [2, 0])
    as_dataframe:           return sessions as a pandas dataframe
    force_cutoff:           whether the animal had to reach the criterion by the 30th of Nov. Only
                            applies to biased and ready for ephys criterion
    Returns
    ---------
    sessions:               The sessions around the criterion day, works in conjunction with
                            any table that has session_start_time as primary key (such as
                            behavior.TrialSet.Trial)
    days:                   The training days around the criterion day. Can be used in conjunction
                            with tables that have session_date as primary key (such as
                            behavior_analysis.BehavioralSummaryByDate)
    """

    from ibl_pipeline import acquisition, subject
    from ibl_pipeline.analyses import behavior as behavior_analysis

    # Query all included subjects
    if force_cutoff is True:
        use_subjects = query_subjects(criterion=criterion).proj("subject_uuid")
    else:
        use_subjects = query_subjects().proj("subject_uuid")

    # Query per subject the date at which the criterion is reached
    sessions = acquisition.Session * behavior_analysis.SessionTrainingStatus
    if criterion == "trained":
        restriction = 'training_status="trained_1a" OR training_status="trained_1b"'
    elif criterion == "biased":
        restriction = 'task_protocol LIKE "%biased%" AND training_status="trained_1b"'
    elif criterion == "ephys":
        restriction = 'training_status LIKE "ready%"'
    else:
        raise ValueError('criterion must be "trained", "biased" or "ephys"')

    subj_crit = (subject.Subject * use_subjects).aggr(
        sessions & restriction,
        "subject_nickname",
        date_criterion="min(date(session_start_time))",
    )

    # Query the training day at which criterion is reached
    subj_crit_day = dj.U("subject_uuid", "day_of_crit") & (
        behavior_analysis.BehavioralSummaryByDate * subj_crit
        & "session_date=date_criterion"
    ).proj(day_of_crit="training_day")

    # Query days around the day at which criterion is reached
    days = (
        behavior_analysis.BehavioralSummaryByDate * subject.Subject * subj_crit_day
        & (
            "training_day - day_of_crit between %d and %d"
            % (-days_from_criterion[0], days_from_criterion[1])
        )
    ).proj("subject_uuid", "subject_nickname", "session_date")

    # Use dates to query sessions
    ses_query = acquisition.Session.aggr(
        days, from_date="min(session_date)", to_date="max(session_date)"
    )

    sessions = (
        acquisition.Session * ses_query
        & "date(session_start_time) >= from_date"
        & "date(session_start_time) <= to_date"
    )

    # Exclude weird sessions
    sessions = sessions & dj.Not([{"session_uuid": u_id} for u_id in EXCLUDED_SESSIONS])

    # Transform to pandas dataframe if necessary
    if as_dataframe is True:
        sessions = sessions.fetch(format="frame").reset_index()
        days = days.fetch(format="frame").reset_index()

    return sessions, days


def query_session_around_performance(perform_thres=0.8, stage="training"):
    """
    Parameters
    ----------
    perform_thres : float, optional
        DESCRIPTION. Performance threshold that need to be met in all 3
        session. The default is 0.8.
    stage:  string, optional.
        DESCRIPTION. Stage of trial too pull from datajoint to calculate
        performance. The default is training. Other options e.g 'biased'
    Returns
    -------
    selection : dataframe
        DESCRIPTION. Dataframe with all trials from mice reaching
        performance criterion
    """
    from ibl_pipeline import behavior, reference, subject

    use_sessions = query_sessions(
        task="all", stable=False, as_dataframe=False, force_cutoff=True, criterion=None
    )
    behav = dj2pandas(
        (
            (
                use_sessions & 'task_protocol LIKE "%' + stage + '%"'
            )  # only get training sessions
            * subject.Subject
            * subject.SubjectLab
            * reference.Lab
            * behavior.TrialSet.Trial
        )
        # Query only the fields we require, reducing the size of the fetch
        .proj(
            "institution_short",
            "subject_nickname",
            "task_protocol",
            "session_uuid",
            "trial_stim_contrast_left",
            "trial_stim_contrast_right",
            "trial_response_choice",
            "task_protocol",
            "trial_stim_prob_left",
            "trial_feedback_type",
            "trial_response_time",
            "trial_stim_on_time",
            "session_end_time",
            "time_zone",
        )
        # Fetch as a pandas DataFrame, ordered by institute
        .fetch(
            order_by="institution_short, subject_nickname, session_start_time, trial_id",
            format="frame",
        ).reset_index()
    )
    behav_ses = (
        behav.groupby(["subject_nickname", "session_start_time"])
        .mean()["correct_easy"]
        .reset_index()
    )
    behav_ses["above_criterion"] = behav_ses["correct_easy"] > perform_thres
    # Check rolling sum of sessions above 0.8, must be 3
    behav_ses["met_session_criterion"] = (
        behav_ses.groupby(["subject_nickname"])["above_criterion"]
        .rolling(3)
        .sum()
        .to_numpy()
    )
    # Select trials from sessions where criterion was first met
    selection = pd.DataFrame()
    for mouse in behav_ses["subject_nickname"].unique():
        mouse_ses = behav_ses[behav_ses["subject_nickname"] == mouse]
        if any(mouse_ses["met_session_criterion"] == 3):
            mouse_ses_select = mouse_ses.iloc[
                np.where(mouse_ses["met_session_criterion"] == 3)[0][0]
                - 2 : np.where(mouse_ses["met_session_criterion"] == 3)[0][0]
                + 1,
                :,
            ]
            trial_select = behav.loc[
                (behav["subject_nickname"] == mouse)
                & (
                    behav["session_start_time"].isin(
                        mouse_ses_select["session_start_time"]
                    )
                )
            ]
            selection = pd.concat([selection, trial_select])
    return selection


# ================================================================== #
# DEFINE PSYCHFUNCFIT TO WORK WITH FACETGRID IN SEABORN
# ================================================================== #


def fit_psychfunc(df):
    choicedat = (
        df.groupby("signed_contrast")
        .agg({"choice": "count", "choice2": "mean"})
        .reset_index()
    )
    if len(choicedat) >= 4:  # need some minimum number of unique x-values
        pars, L = psy.mle_fit_psycho(
            choicedat.values.transpose(),
            P_model="erf_psycho_2gammas",
            parstart=np.array([0, 20.0, 0.05, 0.05]),
            parmin=np.array([choicedat["signed_contrast"].min(), 5, 0.0, 0.0]),
            parmax=np.array([choicedat["signed_contrast"].max(), 40.0, 1, 1]),
        )
    else:
        pars = [np.nan, np.nan, np.nan, np.nan]

    df2 = {
        "bias": pars[0],
        "threshold": pars[1],
        "lapselow": pars[2],
        "lapsehigh": pars[3],
    }
    df2 = pd.DataFrame(df2, index=[0])

    df2["ntrials"] = df["choice"].count()

    return df2


def plot_psychometric(x, y, subj, **kwargs):
    # summary stats - average psychfunc over observers
    df = pd.DataFrame(
        {"signed_contrast": x, "choice": y, "choice2": y, "subject_nickname": subj}
    )
    df2 = (
        df.groupby(["signed_contrast", "subject_nickname"])
        .agg({"choice2": "count", "choice": "mean"})
        .reset_index()
    )
    df2.rename(columns={"choice2": "ntrials", "choice": "fraction"}, inplace=True)
    df2 = df2.groupby(["signed_contrast"]).mean().reset_index()
    df2 = df2[["signed_contrast", "ntrials", "fraction"]]

    # only 'break' the x-axis and remove 50% contrast when 0% is present
    # print(df2.signed_contrast.unique())
    if 0.0 in df2.signed_contrast.values:
        brokenXaxis = True
    else:
        brokenXaxis = False

    # fit psychfunc
    pars, L = psy.mle_fit_psycho(
        df2.transpose().values,  # extract the data from the df
        P_model="erf_psycho_2gammas",
        parstart=np.array([0, 20.0, 0.05, 0.05]),
        parmin=np.array([df2["signed_contrast"].min(), 5, 0.0, 0.0]),
        parmax=np.array([df2["signed_contrast"].max(), 40.0, 1, 1]),
    )

    if brokenXaxis:
        # plot psychfunc
        g = sns.lineplot(
            np.arange(-27, 27),
            psy.erf_psycho_2gammas(pars, np.arange(-27, 27)),
            **kwargs,
        )

        # plot psychfunc: -100, +100
        sns.lineplot(
            np.arange(-36, -31),
            psy.erf_psycho_2gammas(pars, np.arange(-103, -98)),
            **kwargs,
        )
        sns.lineplot(
            np.arange(31, 36),
            psy.erf_psycho_2gammas(pars, np.arange(98, 103)),
            **kwargs,
        )

        # if there are any points at -50, 50 left, remove those
        if 50 in df.signed_contrast.values or -50 in df.signed_contrast.values:
            df.drop(
                df[
                    (df["signed_contrast"] == -50.0) | (df["signed_contrast"] == 50)
                ].index,
                inplace=True,
            )

        # now break the x-axis
        df["signed_contrast"] = df["signed_contrast"].replace(-100, -35)
        df["signed_contrast"] = df["signed_contrast"].replace(100, 35)

    else:
        # plot psychfunc
        g = sns.lineplot(
            np.arange(-103, 103),
            psy.erf_psycho_2gammas(pars, np.arange(-103, 103)),
            **kwargs,
        )

    df3 = (
        df.groupby(["signed_contrast", "subject_nickname"])
        .agg({"choice2": "count", "choice": "mean"})
        .reset_index()
    )

    # plot datapoints with errorbars on top
    if df["subject_nickname"].nunique() > 1:
        # put the kwargs into a merged dict, so that overriding does not cause an error
        sns.lineplot(
            df3["signed_contrast"],
            df3["choice"],
            **{
                **{
                    "err_style": "bars",
                    "linewidth": 0,
                    "linestyle": "None",
                    "mew": 0.5,
                    "marker": "o",
                    "ci": 68,
                },
                **kwargs,
            },
        )

    if brokenXaxis:
        g.set_xticks([-35, -25, -12.5, 0, 12.5, 25, 35])
        g.set_xticklabels(
            ["-100", "-25", "-12.5", "0", "12.5", "25", "100"],
            size="small",
            rotation=60,
        )
        g.set_xlim([-40, 40])
        break_xaxis(y=-0.004)

    else:
        g.set_xticks([-100, -50, 0, 50, 100])
        g.set_xticklabels(["-100", "-50", "0", "50", "100"], size="small", rotation=60)
        g.set_xlim([-110, 110])

    g.set_ylim([0, 1.02])
    g.set_yticks([0, 0.25, 0.5, 0.75, 1])
    g.set_yticklabels(["0", "25", "50", "75", "100"])


def plot_chronometric(x, y, subj, **kwargs):
    df = pd.DataFrame({"signed_contrast": x, "rt": y, "subject_nickname": subj})
    df.dropna(inplace=True)  # ignore NaN RTs
    df2 = (
        df.groupby(["signed_contrast", "subject_nickname"])
        .agg({"rt": "median"})
        .reset_index()
    )
    # df2 = df2.groupby(['signed_contrast']).mean().reset_index()
    df2 = df2[["signed_contrast", "rt", "subject_nickname"]]

    # if 100 in df.signed_contrast.values and not 50 in
    # df.signed_contrast.values:
    df2["signed_contrast"] = df2["signed_contrast"].replace(-100, -35)
    df2["signed_contrast"] = df2["signed_contrast"].replace(100, 35)
    df2 = df2.loc[np.abs(df2.signed_contrast) != 50, :]  # remove those

    ax = sns.lineplot(
        x="signed_contrast",
        y="rt",
        err_style="bars",
        mew=0.5,
        ci=68,
        data=df2,
        **kwargs,
    )

    # all the points
    if df["subject_nickname"].nunique() > 1:
        sns.lineplot(
            x="signed_contrast",
            y="rt",
            err_style="bars",
            mew=0.5,
            linewidth=0,
            marker="o",
            ci=68,
            data=df2,
            **kwargs,
        )

    ax.set_xticks([-35, -25, -12.5, 0, 12.5, 25, 35])
    ax.set_xticklabels(
        ["-100", "-25", "-12.5", "0", "12.5", "25", "100"], size="small", rotation=45
    )
    ax.set_xlim([-40, 40])

    if df["signed_contrast"].min() >= 0:
        ax.set_xlim([-5, 40])
        ax.set_xticks([0, 6, 12.5, 25, 35])
        ax.set_xticklabels(
            ["0", "6.25", "12.5", "25", "100"], size="small", rotation=45
        )


def break_xaxis(y=-0.004, **kwargs):

    # axisgate: show axis discontinuities with a quick hack
    # https://twitter.com/StevenDakin/status/1313744930246811653?s=19
    # first, white square for discontinuous axis
    plt.text(
        -30,
        y,
        "-",
        fontsize=14,
        fontweight="bold",
        horizontalalignment="center",
        verticalalignment="center",
        color="w",
    )
    plt.text(
        30,
        y,
        "-",
        fontsize=14,
        fontweight="bold",
        horizontalalignment="center",
        verticalalignment="center",
        color="w",
    )

    # put little dashes to cut axes
    plt.text(
        -30,
        y,
        "/ /",
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=6,
        fontweight="bold",
    )
    plt.text(
        30,
        y,
        "/ /",
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=6,
        fontweight="bold",
    )


def add_n(x, y, sj, **kwargs):

    df = pd.DataFrame(
        {"signed_contrast": x, "choice": y, "choice2": y, "subject_nickname": sj}
    )

    # ADD TEXT ABOUT NUMBER OF ANIMALS AND TRIALS
    plt.text(
        15,
        0.2,
        "%d mice, %d trials" % (df.subject_nickname.nunique(), df.choice.count()),
        fontweight="normal",
        fontsize=6,
        color="k",
    )


def dj2pandas(behav):

    # make sure all contrasts are positive
    behav["trial_stim_contrast_right"] = np.abs(behav["trial_stim_contrast_right"])
    behav["trial_stim_contrast_left"] = np.abs(behav["trial_stim_contrast_left"])

    behav["signed_contrast"] = (
        behav["trial_stim_contrast_right"] - behav["trial_stim_contrast_left"]
    ) * 100
    # behav['signed_contrast'] = behav.signed_contrast.astype(int)

    behav["trial"] = behav.trial_id  # for psychfuncfit
    val_map = {"CCW": 1, "No Go": 0, "CW": -1}
    behav["choice"] = behav["trial_response_choice"].map(val_map)
    behav["correct"] = np.where(
        np.sign(behav["signed_contrast"]) == behav["choice"], 1, 0
    )
    behav.loc[behav["signed_contrast"] == 0, "correct"] = np.NaN

    behav["choice_right"] = behav.choice.replace(
        [-1, 0, 1], [0, np.nan, 1]
    )  # code as 0, 100 for percentages
    behav["choice2"] = behav.choice_right  # for psychfuncfit
    behav["correct_easy"] = behav.correct
    behav.loc[np.abs(behav["signed_contrast"]) < 50, "correct_easy"] = np.NaN
    behav.rename(columns={"trial_stim_prob_left": "probabilityLeft"}, inplace=True)
    behav["probabilityLeft"] = behav["probabilityLeft"] * 100
    behav["probabilityLeft"] = behav.probabilityLeft.astype(int)

    # compute rt
    if "trial_response_time" in behav.columns:
        behav["rt"] = behav["trial_response_time"] - behav["trial_stim_on_time"]
        # ignore a bunch of things for missed trials
        # don't count RT if there was no response
        behav.loc[behav.choice == 0, "rt"] = np.nan
        # don't count RT if there was no response
        behav.loc[behav.choice == 0, "trial_feedback_type"] = np.nan

    # CODE FOR HISTORY
    behav["previous_choice"] = behav.choice.shift(1)
    behav.loc[behav.previous_choice == 0, "previous_choice"] = np.nan
    behav["previous_outcome"] = behav.trial_feedback_type.shift(1)
    behav.loc[behav.previous_outcome == 0, "previous_outcome"] = np.nan
    behav["previous_contrast"] = np.abs(behav.signed_contrast.shift(1))
    behav["previous_choice_name"] = behav["previous_choice"].map(
        {-1: "left", 1: "right"}
    )
    behav["previous_outcome_name"] = behav["previous_outcome"].map(
        {-1: "post_error", 1: "post_correct"}
    )
    behav["repeat"] = behav.choice == behav.previous_choice

    # # to more easily retrieve specific training days
    # behav['days'] = (behav['session_start_time'] -
    #                  behav['session_start_time'].min()).dt.days

    return behav


def num_star(pvalue):
    if pvalue < 0.05:
        stars = "* p < 0.05"
    elif pvalue < 0.01:
        stars = "** p < 0.01"
    elif pvalue < 0.001:
        stars = "*** p < 0.001"
    elif pvalue < 0.0001:
        stars = "**** p < 0.0001"
    else:
        stars = ""
    return stars
