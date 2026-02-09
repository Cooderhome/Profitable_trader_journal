from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Planner, TradingGoal, JournalEntry
from app import backtest, journal
from .forms import PlannerForm, TradePlanForm
from flask import render_template

planner_bp = Blueprint('planner', __name__, url_prefix='/planner')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@planner_bp.route('/trade-plan/new', methods=['GET', 'POST'])
@login_required
def new_trade_plan():
    """Create a new trade plan"""
    form = TradePlanForm()
    
    if form.validate_on_submit():
        # Convert string prices to float
        entry_price = float(form.entry_price.data) if form.entry_price.data else None
        stop_loss = float(form.stop_loss.data) if form.stop_loss.data else None
        take_profit = float(form.take_profit.data) if form.take_profit.data else None
        risk_amount = float(form.risk_amount.data) if form.risk_amount.data else None
        
        plan = Planner(
            user_id=current_user.id,
            pair=form.pair.data,
            direction=form.direction.data,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            strategy=form.strategy.data,
            goal=form.goal.data,
            analysis=form.analysis.data,
            completed=False
        )
        
        db.session.add(plan)
        db.session.commit()
        flash('Trade plan saved! Remember to execute according to your plan.', 'success')
        return redirect(url_for('planner.trade_plans'))
    
    return render_template('trade_plan_form.html', form=form)

@planner_bp.route('/trade-plans')
@login_required
def trade_plans():
    """List all trade plans"""
    plans = Planner.query.filter_by(user_id=current_user.id).order_by(Planner.date.desc()).all()
    return render_template('trade_plans_list.html', plans=plans)

@planner_bp.route('/performance')
@login_required
def performance():
    """Show performance: planned vs actual trades"""
    # Get all plans
    plans = Planner.query.filter_by(user_id=current_user.id).order_by(Planner.date.desc()).all()
    
    # Get all journal entries
    journals = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.date.desc()).all()
    
    # Calculate adherence metrics
    total_plans = len(plans)
    executed_plans = sum(1 for p in plans if p.completed)
    execution_rate = (executed_plans / total_plans * 100) if total_plans > 0 else 0
    
    # Risk adherence
    risk_violations = 0
    plan_adherence_score = 0
    
    comparisons = []
    for plan in plans:
        if plan.executed_trade_id:
            # Find the corresponding journal entry
            journal = next((j for j in journals if j.id == plan.executed_trade_id), None)
            if journal:
                # Compare plan vs actual
                comparison = {
                    'plan': plan,
                    'actual': journal,
                    'pair_match': plan.pair == journal.pair,
                    'direction_match': plan.direction == journal.direction,
                    'risk_adhered': abs((journal.risk_amount or 0) - (plan.risk_amount or 0)) <= (plan.risk_amount * 0.1) if plan.risk_amount else True,
                    'strategy_match': plan.strategy == journal.strategy if journal.strategy else False
                }
                
                # Calculate adherence score
                score = sum([
                    comparison['pair_match'],
                    comparison['direction_match'],
                    comparison['risk_adhered'],
                    comparison['strategy_match']
                ]) / 4 * 100
                
                comparison['adherence_score'] = score
                plan_adherence_score += score
                
                if not comparison['risk_adhered']:
                    risk_violations += 1
                
                comparisons.append(comparison)
    
    avg_adherence = (plan_adherence_score / len(comparisons)) if comparisons else 0
    
    # AI Guidance
    guidance = generate_guidance(execution_rate, avg_adherence, risk_violations, total_plans)
    
    return render_template('planner_performance.html',
                         total_plans=total_plans,
                         executed_plans=executed_plans,
                         execution_rate=round(execution_rate, 1),
                         avg_adherence=round(avg_adherence, 1),
                         risk_violations=risk_violations,
                         comparisons=comparisons,
                         guidance=guidance)

def generate_guidance(execution_rate, avg_adherence, risk_violations, total_plans):
    """Generate AI-powered guidance based on performance"""
    guidance = {
        'rating': 'Good',
        'color': 'success',
        'messages': []
    }
    
    if total_plans == 0:
        guidance['rating'] = 'Getting Started'
        guidance['color'] = 'info'
        guidance['messages'].append("Start planning your trades to track your discipline and improve consistency.")
        return guidance
    
    # Execution Rate Analysis
    if execution_rate < 30:
        guidance['rating'] = 'Needs Improvement'
        guidance['color'] = 'danger'
        guidance['messages'].append(f"⚠️ You're only executing {execution_rate:.0f}% of your plans. This suggests over-planning or fear of execution.")
    elif execution_rate > 90:
        guidance['messages'].append(f"✅ Excellent execution rate ({execution_rate:.0f}%)! You're following through on your plans.")
    
    # Adherence Analysis
    if avg_adherence < 60:
        guidance['rating'] = 'Poor Discipline'
        guidance['color'] = 'danger'
        guidance['messages'].append(f"⚠️ Your plan adherence is only {avg_adherence:.0f}%. You're deviating significantly from your plans.")
        guidance['messages'].append("💡 Tip: If you can't follow your plan, don't trade. Discipline is everything.")
    elif avg_adherence > 80:
        guidance['messages'].append(f"✅ Great discipline! {avg_adherence:.0f}% plan adherence shows you stick to your strategy.")
    
    # Risk Management
    if risk_violations > 0:
        guidance['rating'] = 'Risk Management Issue'
        guidance['color'] = 'warning'
        guidance['messages'].append(f"⚠️ {risk_violations} trade(s) violated your risk plan. This is dangerous!")
        guidance['messages'].append("💡 Tip: Never risk more than planned. Set hard stops in your platform.")
    else:
        guidance['messages'].append("✅ Perfect risk management! You're staying within your planned risk.")
    
    return guidance


@planner_bp.route('/', methods=['GET', 'POST'])
@login_required
def planner_home():
    """Main Growth Dashboard"""
    
    # 1. Fetch Active Goal
    active_goal = TradingGoal.query.filter_by(user_id=current_user.id, status='active').first()
    
    goal_data = None
    if active_goal:
        # Fetch trades since start date
        trades = JournalEntry.query.filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.date >= datetime.combine(active_goal.start_date, datetime.min.time()),
            JournalEntry.journal_complete == True
        ).order_by(JournalEntry.date.desc()).all()
        
        # Calculate Metrics
        realized_profit = sum((t.profit_loss or 0) for t in trades)
        current_balance = active_goal.start_balance + realized_profit
        progress_pct = min(100, int(((current_balance - active_goal.start_balance) / (active_goal.target_amount - active_goal.start_balance)) * 100)) if active_goal.target_amount > active_goal.start_balance else 0
        
        # Risk Check
        risks = [t.risk_amount for t in trades if t.risk_amount]
        avg_risk = sum(risks) / len(risks) if risks else 0
        risk_status = 'Good'
        if avg_risk > (active_goal.risk_per_trade * 1.1):
            risk_status = 'High'
            
        goal_data = {
            'name': active_goal.name,
            'start': active_goal.start_balance,
            'target': active_goal.target_amount,
            'current': current_balance,
            'profit': realized_profit,
            'progress': progress_pct,
            'deadline': active_goal.deadline,
            'avg_risk': avg_risk,
            'planned_risk': active_goal.risk_per_trade,
            'risk_status': risk_status,
            'trades_count': len(trades)
        }

    # Fetch recent daily plans (keep this for legacy/day-to-day)
    recent_plans = Planner.query.filter_by(user_id=current_user.id).order_by(Planner.date.desc()).limit(5).all()
    
    # We don't handle form submission here anymore, that's moved to dedicated routes
    return render_template('planner.html', goal=goal_data, plans=recent_plans)
@planner_bp.route('/dashboard')
@login_required
def planner_dashboard():
    today = datetime.utcnow().date()
    start_week = today - timedelta(days=today.weekday())  # Monday of current week
    end_week = start_week + timedelta(days=6)  # Sunday

    # Fetch all plans for current week
    weekly_plans = Planner.query.filter(
        Planner.user_id == current_user.id,
        Planner.date >= start_week,
        Planner.date <= end_week
    ).order_by(Planner.date).all()

    # Calculate KPIs
    total_tasks = len(weekly_plans)
    completed_tasks = sum(1 for plan in weekly_plans if plan.completed)
    completion_rate = int((completed_tasks / total_tasks) * 100) if total_tasks else 0

    # Daily completion for chart
    daily_stats = {}
    for i in range(7):
        day = start_week + timedelta(days=i)
        day_plans = [p for p in weekly_plans if p.date == day]
        if day_plans:
            completed = sum(1 for p in day_plans if p.completed)
            daily_stats[day.strftime('%A')] = int((completed / len(day_plans)) * 100)
        else:
            daily_stats[day.strftime('%A')] = 0

    return render_template(
        'dashboardp.html',
        weekly_plans=weekly_plans,
        completion_rate=completion_rate,
        daily_stats=daily_stats
    )

@planner_bp.route('/dashboardfull')
@login_required
def full_dashboard():
    today = datetime.utcnow().date()
    start_week = today - timedelta(days=today.weekday())  # Monday
    end_week = start_week + timedelta(days=6)           # Sunday

    # --- Journal KPIs ---
    journals = JournalEntry.query.filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.date >= datetime.combine(start_week, datetime.min.time()),
        JournalEntry.date <= datetime.combine(end_week, datetime.max.time())
    ).all()
    total_journal = len(journals)
    completed_journal = sum(1 for j in journals if j.journal_complete)
    journaling_percent = int((completed_journal / total_journal) * 100) if total_journal else 0

    # --- Backtest KPIs ---
    backtests = BacktestEntry.query.filter(
        BacktestEntry.user_id == current_user.id,
        BacktestEntry.created_at >= datetime.combine(start_week, datetime.min.time()),
        BacktestEntry.created_at <= datetime.combine(end_week, datetime.max.time())
    ).all()
    total_backtest = len(backtests)
    # completed_backtest = sum(1 for b in backtests if b.completed) # BacktestEntry doesn't have completed?
    # Assume simplified backtest KPI for now
    backtest_percent = int((len(backtests) / 10) * 100)
    backtest_percent = min(100, backtest_percent)


    # --- Planner KPIs ---
    plans = Planner.query.filter(
        Planner.user_id == current_user.id,
        Planner.date >= start_week,
        Planner.date <= end_week
    ).all()
    total_plan = len(plans)
    completed_plan = sum(1 for p in plans if p.completed)
    planner_percent = int((completed_plan / total_plan) * 100) if total_plan else 0

    # --- Aggregate PT Progress (30%) ---
    # Weights: journaling 20%, backtest 20%, planner 20% (30% total PT, discipline 50% separate)
    pt_progress = int((journaling_percent * 0.2 + backtest_percent * 0.2 + planner_percent * 0.2))

    # --- Daily stats for chart ---
    daily_stats = {}
    for i in range(7):
        day = start_week + timedelta(days=i)
        # For simplicity, average % of all 3 KPIs per day
        # Need to fix day matching logic for datetime vs date
        day_j = [j for j in journals if j.date.date() == day]
        day_b = [b for b in backtests if b.created_at.date() == day]
        day_p = [p for p in plans if p.date == day]

        def percent(items):
            if not items: return 0
            # Simplify based on presence
            return 100

        daily_stats[day.strftime('%A')] = int((percent(day_j) + percent(day_b) + percent(day_p)) / 3)

    return render_template(
        'full_dashboard.html',
        journaling_percent=journaling_percent,
        backtest_percent=backtest_percent,
        planner_percent=planner_percent,
        pt_progress=pt_progress,
        daily_stats=daily_stats
    )
@planner_bp.route('/list')
@login_required
def planner_list():
    plans = Planner.query.filter_by(user_id=current_user.id).order_by(Planner.date.desc()).all()
    return render_template('planner_list.html', plans=plans)

@planner_bp.route('/<int:id>')
@login_required
def planner_detail(id):
    plan = Planner.query.get_or_404(id)
    if plan.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('planner.planner_list'))
    return render_template('planner_detail.html', plan=plan)
@planner_bp.route('/goal/new', methods=['GET', 'POST'])
@login_required
def new_goal():
    from .forms import TradingGoalForm
    form = TradingGoalForm()
    
    # Check if active goal exists
    active = TradingGoal.query.filter_by(user_id=current_user.id, status='active').first()
    if active:
        flash('You already have an active plan. Please complete or cancel it first.', 'warning')
        # In a full app, we'd allow managing status or editing
    
    if form.validate_on_submit():
        if active:
             active.status = 'archived' # Archive old goal
             
        goal = TradingGoal(
            user_id=current_user.id,
            name=form.name.data,
            target_amount=form.target_amount.data,
            start_balance=form.start_balance.data,
            win_rate=form.win_rate.data,
            risk_per_trade=form.risk_per_trade.data,
            reward_per_trade=form.reward_per_trade.data,
            lot_size=form.lot_size.data,
            start_date=form.start_date.data,
            deadline=form.deadline.data
        )
        db.session.add(goal)
        db.session.commit()
        flash('New Trading Plan activated!', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('goal_form.html', form=form)
@planner_bp.route('/goal/<int:id>')
@login_required
def goal_detail(id):
    goal = TradingGoal.query.get_or_404(id)
    
    # Ensure user owns this goal
    if goal.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('main.index'))
        
    # Fetch trades contributing to this goal
    trades = JournalEntry.query.filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.date >= datetime.combine(goal.start_date, datetime.min.time()),
        JournalEntry.journal_complete == True
    ).order_by(JournalEntry.date.desc()).all()
    
    current_profit = sum((t.profit_loss or 0) for t in trades)
    progress = min(100, int((current_profit / goal.target_amount) * 100)) if goal.target_amount > 0 else 0
    
    # Risk calc
    risks = [t.risk_amount for t in trades if t.risk_amount]
    avg_risk = sum(risks) / len(risks) if risks else 0.0
    
    warning = None
    if avg_risk > (goal.risk_per_trade * 1.1):
        warning = f"High Risk Warning: You are averaging ${avg_risk:.2f} risk per trade, which is higher than your planned ${goal.risk_per_trade}."

    # --- Plan Feasibility / Greed Analysis ---
    # 1. Risk Percentage
    risk_pct = (goal.risk_per_trade / goal.start_balance) * 100 if goal.start_balance > 0 else 0
    
    # 2. Expectancy
    wr_dec = goal.win_rate / 100.0
    expectancy = (wr_dec * goal.reward_per_trade) - ((1 - wr_dec) * goal.risk_per_trade)
    
    analysis = {
        "rating": "Balanced",
        "color": "success",
        "message": "This plan looks solid and sustainable."
    }
    
    if expectancy <= 0:
        analysis["rating"] = "Negative Edge"
        analysis["color"] = "danger"
        analysis["message"] = "Mathematically, this strategy will lose money over time. Increase Reward or Win Rate."
    elif risk_pct > 5:
        analysis["rating"] = "Extreme Greed (Gambling)"
        analysis["color"] = "danger"
        analysis["message"] = f"You are risking {risk_pct:.1f}% of your account per trade. This is extremely dangerous."
    elif risk_pct > 2.5:
        analysis["rating"] = "Aggressive"
        analysis["color"] = "warning"
        analysis["message"] = f"Risking {risk_pct:.1f}% is aggressive. Be careful of drawdown streaks."
    
    return render_template(
        'goal_detail.html', 
        goal=goal, 
        trades=trades, 
        current_profit=current_profit, 
        progress=progress, 
        avg_risk=avg_risk, 
        warning=warning,
        analysis=analysis
    )

@planner_bp.route('/goal/<int:id>/complete', methods=['POST'])
@login_required
def complete_goal(id):
    goal = TradingGoal.query.get_or_404(id)
    if goal.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('main.index'))
        
    goal.status = 'completed'
    db.session.commit()
    flash(f'Congratulations! {goal.name} marked as completed. Time for a new target!', 'success')
    return redirect(url_for('main.index'))
