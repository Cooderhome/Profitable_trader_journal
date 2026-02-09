# app/journal/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, FileField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Optional
import re

class CurrencyFloatField(FloatField):
    """Custom FloatField that strips currency symbols and formatting before validation"""
    
    def process_formdata(self, valuelist):
        if valuelist:
            value = valuelist[0]
            print(f"[DEBUG] CurrencyFloatField processing: {repr(value)}")
            
            if value:
                # Remove currency symbols (₺, $, €, £, ¥, etc.), commas, and spaces
                # This regex removes any non-digit characters except decimal point and minus sign
                cleaned = re.sub(r'[^\d.-]', '', value)
                print(f"[DEBUG] CurrencyFloatField cleaned: {repr(cleaned)}")
                
                # Update the value in the list
                valuelist[0] = cleaned if cleaned else ''
        
        # Call parent's process_formdata with cleaned value
        return super(CurrencyFloatField, self).process_formdata(valuelist)

class JournalForm(FlaskForm):
    # Before trade
    pair = StringField("Pair (e.g., XAUUSD)", validators=[DataRequired()])
    linked_plan = SelectField("Link to Plan", choices=[], coerce=int, validate_choice=False) # Dynamic choices
    direction = SelectField("Direction", choices=[('buy', 'Buy'), ('sell', 'Sell')])
    entry_price = CurrencyFloatField("Entry Price", validators=[Optional()])
    stop_loss = CurrencyFloatField("Stop Loss", validators=[Optional()])
    risk_amount = CurrencyFloatField("Risk Amount ($)", validators=[Optional()])
    take_profit = CurrencyFloatField("Take Profit", validators=[Optional()])
    lot_size = CurrencyFloatField("Lot Size", validators=[Optional()])
    pre_trade_analysis = TextAreaField("Before Trade Analysis")
    before_image = FileField("Before Trade Screenshot")

    # Checklist / Process
    news_checked = BooleanField("Checked News?")
    rules_followed = BooleanField("Followed All Rules?")
    
    # New Fields
    strategy = StringField("Strategy (e.g. Breakout)")
    risk_reward = CurrencyFloatField("Risk:Reward Ratio (R)", validators=[Optional()])
    news_event = StringField("News Event (if any)")

    # After trade
    result = SelectField("Result", choices=[('win', 'Win'), ('loss', 'Loss'), ('be', 'Break-Even')], validators=[Optional()])
    profit_loss = CurrencyFloatField("Profit/Loss", validators=[Optional()])
    reflection = TextAreaField("Reflection After Trade")
    mistakes = TextAreaField("Mistakes")
    after_image = FileField("After Trade Screenshot")
    
    # Conclusion
    journal_complete = BooleanField("Mark Journal Complete?")

    submit = SubmitField("Save Journal Entry")

class ImportJournalForm(FlaskForm):
    csv_file = FileField("Upload CSV (MetaTrader/cTrader)", validators=[DataRequired()])
    submit = SubmitField("Import Trades")

