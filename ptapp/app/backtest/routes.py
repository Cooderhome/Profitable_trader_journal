import os
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models import BacktestEntry
from .forms import BacktestForm
from collections import defaultdict

backtest_bp = Blueprint('backtest', __name__, url_prefix='/backtest')

@backtest_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_backtest():
    form = BacktestForm()
    if form.validate_on_submit():
        after_img = None

        if form.after_image.data:
            after_file = form.after_image.data
            after_img = secure_filename(after_file.filename)
            upload_path = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_path, exist_ok=True)
            after_file.save(os.path.join(upload_path, after_img))

        # Convert string prices to float
        entry_price = float(form.entry_price.data) if form.entry_price.data else None
        exit_price = float(form.exit_price.data) if form.exit_price.data else None

        entry = BacktestEntry(
            user_id=current_user.id,
            strategy_name=form.strategy_name.data,
            pair=form.pair.data,
            entry_time=form.entry_time.data,
            exit_time=form.exit_time.data,
            entry_price=entry_price,
            exit_price=exit_price,
            result=form.result.data,
            notes=form.notes.data,
            image_filename=after_img
        )

        db.session.add(entry)
        db.session.commit()
        flash("Backtest saved successfully!", "success")
        return redirect(url_for('backtest.list_backtests'))

    return render_template('backtest_form.html', form=form)


@backtest_bp.route('/list')
@login_required
def list_backtests():
    entries = BacktestEntry.query.filter_by(user_id=current_user.id).order_by(BacktestEntry.created_at.desc()).all()
    return render_template('backtest_list.html', entries=entries)


@backtest_bp.route('/view/<int:entry_id>')
@login_required
def view_backtest(entry_id):
    entry = BacktestEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('backtest.list_backtests'))
    return render_template('backtest_detail.html', entry=entry)


@backtest_bp.route('/analytics')
@login_required
def analytics():
    """Show backtest analytics and strategy performance"""
    entries = BacktestEntry.query.filter_by(user_id=current_user.id).all()
    
    if not entries:
        return render_template('backtest_analytics.html', 
                             total_trades=0,
                             strategies={})
    
    # Overall Stats
    total_trades = len(entries)
    wins = sum(1 for e in entries if e.result == 'win')
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate P/L
    total_pnl = 0
    gross_profit = 0
    gross_loss = 0
    
    for e in entries:
        if e.entry_price and e.exit_price:
            pnl = e.exit_price - e.entry_price
            total_pnl += pnl
            if pnl > 0:
                gross_profit += pnl
            else:
                gross_loss += abs(pnl)
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    
    # Per-Strategy Stats
    strategy_stats = defaultdict(lambda: {
        'total': 0,
        'wins': 0,
        'losses': 0,
        'pnl': 0,
        'gross_profit': 0,
        'gross_loss': 0
    })
    
    for e in entries:
        strategy = e.strategy_name or 'Unnamed Strategy'
        stats = strategy_stats[strategy]
        stats['total'] += 1
        
        if e.result == 'win':
            stats['wins'] += 1
        else:
            stats['losses'] += 1
        
        if e.entry_price and e.exit_price:
            pnl = e.exit_price - e.entry_price
            stats['pnl'] += pnl
            if pnl > 0:
                stats['gross_profit'] += pnl
            else:
                stats['gross_loss'] += abs(pnl)
    
    # Calculate derived metrics for each strategy
    for strategy, stats in strategy_stats.items():
        stats['win_rate'] = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
        stats['profit_factor'] = (stats['gross_profit'] / stats['gross_loss']) if stats['gross_loss'] > 0 else 0
    
    return render_template('backtest_analytics.html',
                         total_trades=total_trades,
                         wins=wins,
                         losses=losses,
                         win_rate=round(win_rate, 1),
                         total_pnl=round(total_pnl, 2),
                         profit_factor=round(profit_factor, 2),
                         strategies=dict(strategy_stats))

