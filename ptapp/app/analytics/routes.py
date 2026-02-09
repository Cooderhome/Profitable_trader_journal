from flask import render_template
from flask_login import login_required, current_user
from app.models import JournalEntry
from . import analytics_bp
from datetime import datetime, timedelta
from app.extensions import db
from sqlalchemy import func

@analytics_bp.route('/')
@login_required
def dashboard():
    # Fetch all journal entries for the user
    entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.date).all()

    # --- Weekly Analytics ---
    # Group by week number/start date
    weekly_data = {}
    
    # --- Monthly Analytics ---
    monthly_data = {}
    
    # --- Yearly Analytics ---
    yearly_data = {}
    
    # --- Heatmap Data ---
    # Format: { 'yyyy-mm-dd': profit_loss }
    heatmap_data = {}
    
    # --- Win/Loss Rates ---
    weekly_win_loss = {} # { 'Week Start': {'wins': 0, 'losses': 0} }
    monthly_win_loss = {}

    for entry in entries:
        if not entry.date or entry.profit_loss is None:
            continue
            
        date_str = entry.date.strftime('%Y-%m-%d')
        
        # Heatmap
        # Aggregate P/L for the day
        heatmap_data[date_str] = heatmap_data.get(date_str, 0) + entry.profit_loss

        # Weekly (Identify by Monday of the week)
        week_start = entry.date - timedelta(days=entry.date.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        
        weekly_data[week_key] = weekly_data.get(week_key, 0) + entry.profit_loss
        
        if week_key not in weekly_win_loss:
            weekly_win_loss[week_key] = {'wins': 0, 'losses': 0, 'be': 0}
            
        if entry.profit_loss > 0:
            weekly_win_loss[week_key]['wins'] += 1
        elif entry.profit_loss < 0:
            weekly_win_loss[week_key]['losses'] += 1
        else:
            weekly_win_loss[week_key]['be'] += 1

        # Monthly
        month_key = entry.date.strftime('%Y-%m') # "2023-10"
        monthly_data[month_key] = monthly_data.get(month_key, 0) + entry.profit_loss
        
        if month_key not in monthly_win_loss:
            monthly_win_loss[month_key] = {'wins': 0, 'losses': 0, 'be': 0}
            
        if entry.profit_loss > 0:
            monthly_win_loss[month_key]['wins'] += 1
        elif entry.profit_loss < 0:
            monthly_win_loss[month_key]['losses'] += 1
        else:
            monthly_win_loss[month_key]['be'] += 1

        # Yearly
        year_key = entry.date.strftime('%Y')
        yearly_data[year_key] = yearly_data.get(year_key, 0) + entry.profit_loss

    # Sort data for charts
    sorted_weeks = sorted(weekly_data.keys())
    chart_weekly_labels = sorted_weeks
    chart_weekly_values = [weekly_data[k] for k in sorted_weeks]
    
    chart_weekly_wins = [weekly_win_loss[k]['wins'] for k in sorted_weeks]
    chart_weekly_losses = [weekly_win_loss[k]['losses'] for k in sorted_weeks]

    sorted_months = sorted(monthly_data.keys())
    chart_monthly_labels = sorted_months
    chart_monthly_values = [monthly_data[k] for k in sorted_months]
    
    chart_monthly_wins = [monthly_win_loss[k]['wins'] for k in sorted_months]
    chart_monthly_losses = [monthly_win_loss[k]['losses'] for k in sorted_months]

    sorted_years = sorted(yearly_data.keys())
    chart_yearly_labels = sorted_years
    chart_yearly_values = [yearly_data[k] for k in sorted_years]

    return render_template('analytics.html',
                           heatmap_data=heatmap_data,
                           chart_weekly_labels=chart_weekly_labels,
                           chart_weekly_values=chart_weekly_values,
                           chart_weekly_wins=chart_weekly_wins,
                           chart_weekly_losses=chart_weekly_losses,
                           chart_monthly_labels=chart_monthly_labels,
                           chart_monthly_values=chart_monthly_values,
                           chart_monthly_wins=chart_monthly_wins,
                           chart_monthly_losses=chart_monthly_losses,
                           chart_yearly_labels=chart_yearly_labels,
                           chart_yearly_values=chart_yearly_values)
