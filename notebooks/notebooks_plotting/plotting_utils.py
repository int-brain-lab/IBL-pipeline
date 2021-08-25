from ibl_pipeline.analyses import behavior
from ibl_pipeline import behavior as behavior_ingest
from ibl_pipeline import subject, action, acquisition
from ibl_pipeline.utils import psychofit as psy
from uuid import UUID
import numpy as np
import datetime
import datajoint as dj
import plotly.graph_objs as go
import pandas as pd
import seaborn as sns
import plotly
from plotly import tools


def get_date_range(subj):
    
    # get date range of session
    first_session_date, last_session_date = subj.aggr(
        acquisition.Session, 
        first_session_date='min(DATE(session_start_time))',
        last_session_date='max(DATE(session_end_time))').fetch1(
            'first_session_date', 'last_session_date'
    )
    
    # get date range of water restriction
    first_water_res_date, last_water_res_date = subj.aggr(
        action.WaterRestriction, 
        first_res_date='min(DATE(restriction_start_time))',
        last_res_date='max(DATE(restriction_end_time))').fetch1(
            'first_res_date', 'last_res_date')
    
    # get date range of water administration
    first_water_admin_date, last_water_admin_date = subj.aggr(
        action.WaterAdministration, 
        first_admin_date='min(DATE(administration_time))',
        last_admin_date='max(DATE(administration_time))').fetch1(
            'first_admin_date', 'last_admin_date')
    
    # get date range of weighing
    first_weighing_date, last_weighing_date = subj.aggr(
        action.Weighing, 
        first_weighing_date='min(DATE(weighing_time))',
        last_weighing_date='max(DATE(weighing_time))').fetch1(
            'first_weighing_date', 'last_weighing_date')
    
    # get overall date range
    first_date = min([first_session_date, first_water_res_date, first_water_admin_date, first_weighing_date]) \
                  - datetime.timedelta(days=3)
    
    if last_water_res_date:
        last_date = np.nanmax([last_session_date, last_water_res_date, last_water_admin_date, last_weighing_date]) \
                  + datetime.timedelta(days=3)
    else:
        last_date = np.nanmax([last_session_date, last_water_admin_date, last_weighing_date]) \
                  + datetime.timedelta(days=3)

    first_date_str = first_date.strftime('%Y-%m-%d')
    last_date_str = last_date.strftime('%Y-%m-%d')

    date_array = [first_date + datetime.timedelta(days=day) for day in range(0, (last_date-first_date).days)]

    # get Mondays
    mondays = [day.strftime('%Y-%m-%d') 
               for day in date_array if day.weekday()==0]
    
    return dict(
        first_date=first_date,
        last_date=last_date,
        first_date_str=first_date_str,
        last_date_str=last_date_str,
        date_array=date_array,
        mondays=mondays)
  
def get_status(subj):
    # get the first date when animal became "trained" and "ready for ephys"
    first_trained = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "trained"', 
        first_session='DATE(min(session_start_time))')
    first_biased = subj.aggr(
        behavior.SessionTrainingStatus & 'training_status = "ready for ephys"', 
        first_session='DATE(min(session_start_time))')
    
    result = dict()
    if len(first_trained):
        first_trained_date = first_trained.fetch1('first_session').strftime('%Y-%m-%d')
        result.update(is_trained=True, first_trained_date=first_trained_date)
    else:
        result.update(is_trained=False)

    if len(first_biased):
        first_biased_date = first_biased.fetch1('first_session').strftime('%Y-%m-%d')
        result.update(is_biased=True, first_biased_date=first_biased_date)
    else:
        result.update(is_biased=False)
    
    return result

def create_status_plot(data, yrange, status, xaxis='x1', yaxis='y1', show_legend_external=True):
    
    if status['is_trained']:
        data.append(
           go.Scatter(
               x=[status['first_trained_date'], status['first_trained_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='orange'),
               name='first day got trained',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               legendgroup='status'
            ) 
        )
    
    if status['is_biased']:
        data.append(
           go.Scatter(
               x=[status['first_biased_date'], status['first_biased_date']],
               y=yrange,
               mode="lines",
               marker=dict(color='forestgreen'),
               name='first day got biased',
               xaxis=xaxis,
               yaxis=yaxis,
               showlegend=show_legend_external,
               legendgroup='status'
            ) 
        )
    
    return data
  

def create_monday_plot(data, yrange, mondays, xaxis='x1', yaxis='y1', show_legend_external=True):
 
    for imonday, monday in enumerate(mondays):
        if imonday==0 and show_legend_external:
            show_legend = True
        else:
            show_legend = False     
    
        data.append(
            go.Scatter(
                x=[monday, monday],
                y=yrange,
                mode="lines",
                line=dict(
                    width=0.5,
                    color='gray',
                    dash='dot'
                ),
                name='Mondays',
                xaxis=xaxis,
                yaxis=yaxis,
                showlegend=show_legend,
                legendgroup='monday',
                hoverinfo='skip'
            )
        )
        
    return data


def get_color(prob_left, opacity=0.3):
    
    cmap = sns.diverging_palette(20, 220, n=3, center="dark")
    
    if prob_left == 0.2:
        color = cmap[0]
        err_c = color.copy()
        err_c[3] = err_c[3]*opacity
        curve_color = 'rgba{}'.format(tuple(color))
        error_color = 'rgba{}'.format(tuple(err_c))
    elif prob_left == 0.5:
        color = cmap[1]
        err_c = color.copy()
        err_c[3] = err_c[3]*opacity
        curve_color = 'rgba{}'.format(tuple(color))
        error_color = 'rgba{}'.format(tuple(err_c))
    elif prob_left == 0.8:
        color = cmap[2]
        err_c = color.copy()
        err_c[3] = err_c[3]*opacity
        curve_color = 'rgba{}'.format(tuple(color))
        error_color = 'rgba{}'.format(tuple(err_c))
    else:
        return
    
    return curve_color, error_color


                
                