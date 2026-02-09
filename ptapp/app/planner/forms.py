from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, Optional
from datetime import datetime
import re

class CurrencyFloatField(StringField):
    """Custom field that strips currency symbols and formatting before validation"""
    
    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0]
            if value:
                # Remove currency symbols (₺, $, €, £, ¥, etc.), commas, and spaces
                cleaned = re.sub(r'[^\d.-]', '', value)
                valuelist[0] = cleaned if cleaned else ''
        return super(CurrencyFloatField, self).process_formdata(valuelist)

class TradePlanForm(FlaskForm):
    """Form for planning a trade in advance"""
    # Trade Setup
    pair = StringField('Pair', validators=[DataRequired()], 
                      render_kw={"placeholder": "e.g., XAUUSD"})
    direction = SelectField('Direction', 
                           choices=[('buy', 'Buy'), ('sell', 'Sell')],
                           validators=[DataRequired()])
    
    entry_price = CurrencyFloatField('Planned Entry Price', validators=[DataRequired()],
                                    render_kw={"placeholder": "e.g., 2650.50"})
    stop_loss = CurrencyFloatField('Stop Loss', validators=[DataRequired()],
                                  render_kw={"placeholder": "e.g., 2645.00"})
    take_profit = CurrencyFloatField('Take Profit', validators=[DataRequired()],
                                    render_kw={"placeholder": "e.g., 2660.00"})
    risk_amount = CurrencyFloatField('Risk Amount ($)', validators=[DataRequired()],
                                    render_kw={"placeholder": "e.g., 10.00"})
    
    strategy = StringField('Strategy', validators=[DataRequired()],
                          render_kw={"placeholder": "e.g., Breakout, Trend Following"})
    
    # Plan Description
    goal = StringField('Today\'s Trading Goal', validators=[DataRequired()],
                      render_kw={"placeholder": "e.g., Execute 1 high-quality setup"})
    analysis = TextAreaField('Pre-Trade Analysis', validators=[DataRequired()],
                            render_kw={"placeholder": "Why are you taking this trade? What's your edge?"})
    
    submit = SubmitField('Save Trade Plan')

class PlannerForm(FlaskForm):
    """Legacy form for general daily planning"""
    goal = StringField('Daily Goal', validators=[DataRequired()])
    tasks = TextAreaField('Tasks for Today', validators=[DataRequired()])
    reflection = TextAreaField('Reflection (optional)')
    completed = BooleanField('Mark as Completed')
    submit = SubmitField('Save Plan')

class TradingGoalForm(FlaskForm):
    """Form for setting long-term trading goals"""
    name = StringField('Goal Name (e.g., Buy a Phone)', validators=[DataRequired()])
    target_amount = FloatField('Target Profit Amount ($)', validators=[DataRequired()])
    start_balance = FloatField('Starting Balance ($)', validators=[DataRequired()])
    
    # Strategy Params
    win_rate = FloatField('Strategy Win Rate (%)', default=50.0)
    risk_per_trade = FloatField('Risk per Trade ($)', default=10.0)
    reward_per_trade = FloatField('Reward per Trade ($)', default=20.0)
    lot_size = FloatField('Lot Size (e.g. 0.01)', default=0.01)
    
    start_date = DateField('Start Date', format='%Y-%m-%d', default=datetime.utcnow, validators=[DataRequired()])
    deadline = DateField('Target Date (Deadline)', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Create Trading Plan')

