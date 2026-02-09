from flask import Blueprint, render_template, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from app.models import JournalEntry, BacktestEntry, TradingGoal
from app.extensions import db

main_bp = Blueprint("main", __name__, template_folder="templates", static_folder="../../static")

def compute_weekly_kpis(user_id=1, start_date=None):
    """
    Compute simple weekly KPI scores for user.
    Each component returns a 0..1 value. Overall is average * 100.
    This is intentionally simple and easy to tweak.
    """
    if start_date is None:
        # week start = Monday of current week
        today = date.today()
        start_date = today - timedelta(days=today.weekday())

    # end date inclusive
    end_date = start_date + timedelta(days=6)

    # Query DB for journals and backtests in that week
    journals = JournalEntry.query.filter(
        JournalEntry.user_id == user_id,
        JournalEntry.date >= datetime.combine(start_date, datetime.min.time()),
        JournalEntry.date <= datetime.combine(end_date, datetime.max.time())
    ).all()

    backtests = BacktestEntry.query.filter(
        BacktestEntry.user_id == user_id,
        BacktestEntry.created_at >= datetime.combine(start_date, datetime.min.time()),
        BacktestEntry.created_at <= datetime.combine(end_date, datetime.max.time())
    ).all()

    # 1. Journaling Score: Consistency (Days traded / 5)
    # Did user log at least one trade on distinct days?
    unique_days = set(j.date.date() for j in journals)
    journaling_score = min(1.0, len(unique_days) / 5)

    # 2. Backtest Score: Volume (Target: 10 backtests / week)
    backtest_score = min(1.0, len(backtests) / 10)

    # 3. Risk Score: Adherence to plan
    # If active goal, check if risk <= planned risk. Else check rules_followed.
    risk_score = 0.0
    active_goal = TradingGoal.query.filter_by(user_id=user_id, status='active').first()
    
    if journals:
        risk_compliant_count = 0
        for j in journals:
            # If we have a goal and risk amount recorded, check limit
            if active_goal and j.risk_amount and active_goal.risk_per_trade:
                # Allow 5% buffer
                if j.risk_amount <= (active_goal.risk_per_trade * 1.05):
                    risk_compliant_count += 1
            # Fallback to self-reported rule adherence
            elif j.rules_followed:
                risk_compliant_count += 1
                
        risk_score = risk_compliant_count / len(journals)

    # 4. Execution Score: Error Free % (Trades with empty 'mistakes')
    execution_score = 0.0
    if journals:
        # If 'mistakes' field is empty or short, consider it good execution
        good_exec_count = sum(1 for j in journals if not j.mistakes or len(j.mistakes) < 5)
        execution_score = good_exec_count / len(journals)

    # 5. Discipline Score: Process (News Checked + Complete Journal)
    discipline_score = 0.0
    if journals:
        # Strict: Must have checked news AND marked journal complete
        disciplined_count = sum(1 for j in journals if j.news_checked and j.journal_complete)
        discipline_score = disciplined_count / len(journals)

    total = (journaling_score + backtest_score + risk_score + execution_score + discipline_score) / 5 * 100

    return {
        "week_start": start_date,
        "journaling": int(journaling_score * 100),
        "backtest": int(backtest_score * 100),
        "risk": int(risk_score * 100),
        "execution": int(execution_score * 100),
        "discipline": int(discipline_score * 100),
        "total": int(total)
    }

@main_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return render_template('landing.html')
        
    # Simple single-user demo (user_id=1). Replace with current_user.id later.
    kpis = compute_weekly_kpis(user_id=current_user.id)
    bible_verse = "Colossians 3:23 — Whatever you do, work heartily, as for the Lord and not for men."
    # Fetch Active Goal
    active_goal = TradingGoal.query.filter_by(user_id=current_user.id, status='active').first()
    goal_data = None
    
    if active_goal:
        # Calculate Realized P/L since goal start
        # Note: In a real app we'd sum profit_loss from Closed trades
        trades_since_start = JournalEntry.query.filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.date >= datetime.combine(active_goal.start_date, datetime.min.time()),
            JournalEntry.journal_complete == True
        ).all()
        
        current_profit = sum((t.profit_loss or 0) for t in trades_since_start)
        current_eq = active_goal.start_balance + current_profit
        
        # Projection Logic
        # Expected value/trade = (Win% * Reward) - (Loss% * Risk)
        # WR=72, R=$12.5, Risk=$5. EV = (0.72*12.5) - (0.28*5) = 9 - 1.4 = 7.6
        # Projection Logic
        wr_dec = active_goal.win_rate / 100.0
        ev_per_trade = (wr_dec * active_goal.reward_per_trade) - ((1 - wr_dec) * active_goal.risk_per_trade)
        
        remaining_needed = active_goal.target_amount - current_profit
        trades_to_go = 0
        if remaining_needed > 0 and ev_per_trade > 0:
            trades_to_go = int(remaining_needed / ev_per_trade) + 1
            
        progress_pct = min(100, int((current_profit / active_goal.target_amount) * 100))
        
        # Risk Warning Logic
        warning = None
        recent_risks = [t.risk_amount for t in trades_since_start if t.risk_amount]
        if recent_risks:
            avg_risk = sum(recent_risks) / len(recent_risks)
            # Tolerance: Allow up to 10% deviation (1.1x)
            if avg_risk > (active_goal.risk_per_trade * 1.1):
                warning = f"High Risk Warning: You are risking ${avg_risk:.2f} avg vs planned ${active_goal.risk_per_trade}."
        
        goal_data = {
            "id": active_goal.id,
            "name": active_goal.name,
            "target": active_goal.target_amount,
            "current": current_profit,
            "balance": current_eq,
            "progress": progress_pct,
            "ev": round(ev_per_trade, 2),
            "trades_to_go": trades_to_go,
            "deadline": active_goal.deadline,
            "warning": warning
        }


    return render_template(
        "dashboard.html",
        journaling=kpis["journaling"],
        backtest=kpis["backtest"],
        risk=kpis["risk"],
        execution=kpis["execution"],
        discipline=kpis["discipline"],
        total=kpis["total"],
        bible_verse=bible_verse,
        week_start=kpis["week_start"],
        goal=goal_data
    )

@main_bp.route("/subscription")
@login_required
def subscription():
    return render_template("subscription.html")

@main_bp.route("/subscription/upgrade", methods=['POST'])
@login_required
def upgrade_pro():
    from app.models import Subscription
    
    # Check if sub exists
    sub = Subscription.query.filter_by(user_id=current_user.id).first()
    if not sub:
        sub = Subscription(user_id=current_user.id)
        db.session.add(sub)
    
    # Upgrade Logic (Mock)
    sub.plan_type = 'pro'
    sub.is_active = True
    sub.start_date = datetime.utcnow()
    # In real app, stripe_customer_id would be set here
    
    db.session.commit()
    flash('Welcome to Pro! You now have access to all premium features.', 'success')
    return redirect(url_for('main.index'))
