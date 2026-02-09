# app/journal/routes.py
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from app.extensions import db
from app.models import JournalEntry, TradingGoal

@journal_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_journal_entry():
    form = JournalForm()
    
    # Populate Plan Choices
    active_plans = TradingGoal.query.filter_by(user_id=current_user.id, status='active').all()
    form.linked_plan.choices = [(0, 'Normal Trade (No Plan)')] + [(p.id, p.name) for p in active_plans]
    
    # Debug: Print form data if POST
    if request.method == 'POST':
        print(f"\n[DEBUG] Form submitted!")
        print(f"[DEBUG] entry_price raw value: {repr(request.form.get('entry_price'))}")
        print(f"[DEBUG] All form data: {dict(request.form)}")
    
    # Check Plan Limits
    if not current_user.is_pro:
        entry_count = JournalEntry.query.filter_by(user_id=current_user.id).count()
        if entry_count >= 50:
            flash('Free plan limit reached (50 trades). Please upgrade to Pro for unlimited journaling.', 'warning')
            return redirect(url_for('journal.list_journals'))

    if form.validate_on_submit():
        # Save uploaded images
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        before_filename = None
        after_filename = None

        if form.before_image.data:
            before_filename = secure_filename(form.before_image.data.filename)
            form.before_image.data.save(os.path.join(upload_folder, before_filename))

        if form.after_image.data:
            after_filename = secure_filename(form.after_image.data.filename)
            form.after_image.data.save(os.path.join(upload_folder, after_filename))

        # Calculate AI confidence before trade
        inputs = predictor.prepare_inputs(form=form)
        confidence = predictor.predict(inputs)
        # Normalize to 0-1 range
        confidence = max(0.0, min(1.0, confidence))

        # Create new journal entry
        entry = JournalEntry(
            user_id=current_user.id,
            pair=form.pair.data,
            direction=form.direction.data,
            
            # Link to Plan (if selected and not 0)
            trading_goal_id=form.linked_plan.data if form.linked_plan.data != 0 else None,
            
            entry_price=form.entry_price.data,
            stop_loss=form.stop_loss.data,
            risk_amount=form.risk_amount.data,
            take_profit=form.take_profit.data,
            lot_size=form.lot_size.data,
            pre_trade_analysis=form.pre_trade_analysis.data,
            before_image=before_filename,
            
            # KPI fields
            news_checked=form.news_checked.data,
            rules_followed=form.rules_followed.data,
            journal_complete=form.journal_complete.data,

            # New Analysis Fields
            strategy=form.strategy.data,
            risk_reward=form.risk_reward.data,
            news_event=form.news_event.data,
            ai_confidence=confidence, # Save calculated confidence

            result=form.result.data,
            profit_loss=form.profit_loss.data,
            reflection=form.reflection.data,
            mistakes=form.mistakes.data,
            after_image=after_filename,
        )

        db.session.add(entry)
        db.session.commit()
        
        # If result is already provided (e.g. historical entry), learn instantly
        if entry.result:
             predictor.learn_from_entry(entry)

        flash(f'Journal entry added! AI Trade Confidence: {round(confidence * 100)}%', 'success')
        return redirect(url_for('journal.list_journals'))
    
    # Debug: Print validation errors
    if form.errors:
        print(f"\n[DEBUG] Form validation errors: {form.errors}")
        for field, errors in form.errors.items():
            print(f"[DEBUG] Field '{field}' errors: {errors}")
            if hasattr(form, field):
                field_obj = getattr(form, field)
                print(f"[DEBUG] Field '{field}' raw_data: {field_obj.raw_data}")
                print(f"[DEBUG] Field '{field}' data: {field_obj.data}")

    return render_template('journal_form.html', form=form)

@journal_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_journal():
    if not current_user.is_pro:
        flash("Import is a Pro feature. Please upgrade.", "warning")
        return redirect(url_for('journal.list_journals'))

    from .forms import ImportJournalForm
    form = ImportJournalForm()
    
    if form.validate_on_submit():
        import csv
        from io import TextIOWrapper
        
        file = form.csv_file.data
        # Simple CSV parsing (Naive implementation for demo)
        # In a real app, use pandas or flexible mapping logic
        stream = TextIOWrapper(file.stream, encoding='utf-8')
        csv_input = csv.DictReader(stream)
        
        count = 0
        for row in csv_input:
            # Attempt to find common headers
            # Date/Time
            date_str = row.get('Time') or row.get('Date') or row.get('Open Time')
            if not date_str: continue # Skip invalid
            
            # Simple Date Parsing (Assuming YYYY.MM.DD HH:MM:SS or similar)
            # This is fragile, but sufficient for a "demo" of the feature
            try:
                # Try standard MT4 format: 2023.10.25 14:00:00
                trade_date = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')
            except:
                try:
                    trade_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except:
                     trade_date = datetime.utcnow() # Fallback

            # Pair
            pair = row.get('Symbol') or row.get('Item') or row.get('Pair')
            
            # Type
            direction = row.get('Type') or row.get('Direction') # buy/sell
            
            # Price
            open_price = row.get('Open') or row.get('Price') or row.get('Entry Price')
            
            # Profit
            profit = row.get('Profit') or row.get('Amount') or row.get('Net')
            
            if pair and direction:
                entry = JournalEntry(
                    user_id=current_user.id,
                    date=trade_date,
                    pair=pair,
                    direction=direction.lower(),
                    entry_price=float(open_price) if open_price else 0.0,
                    profit_loss=float(profit) if profit else 0.0,
                    result='win' if float(profit or 0) > 0 else 'loss',
                    journal_complete=False # Needs review
                )
                db.session.add(entry)
                count += 1
        
        db.session.commit()
        flash(f'Successfully imported {count} trades from CSV.', 'success')
        return redirect(url_for('journal.list_journals'))
        
    return render_template('import_journal.html', form=form)

@journal_bp.route('/list')
@login_required
def list_journals():
    entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.date.desc()).all()
    return render_template('journal_list.html', entries=entries)


@journal_bp.route('/view/<int:entry_id>')
@login_required
def view_journal(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('journal.list_journals'))
    return render_template('journal_detail.html', entry=entry)