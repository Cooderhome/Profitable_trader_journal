from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeField, TextAreaField, FileField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional
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

class BacktestForm(FlaskForm):
    strategy_name = StringField("Strategy Name", validators=[DataRequired()], 
                                render_kw={"placeholder": "e.g., Breakout Strategy"})
    pair = StringField("Pair", validators=[DataRequired()], 
                      render_kw={"placeholder": "e.g., XAUUSD"})
    
    entry_time = DateTimeField("Entry Time", validators=[DataRequired()], 
                               format='%Y-%m-%dT%H:%M')
    exit_time = DateTimeField("Exit Time", validators=[DataRequired()], 
                             format='%Y-%m-%dT%H:%M')
    
    entry_price = CurrencyFloatField("Entry Price", validators=[DataRequired()],
                                    render_kw={"placeholder": "e.g., 2650.50"})
    exit_price = CurrencyFloatField("Exit Price", validators=[DataRequired()],
                                   render_kw={"placeholder": "e.g., 2655.00"})
    
    result = SelectField("Result", 
                        choices=[('win', 'Win'), ('loss', 'Loss')],
                        validators=[DataRequired()])
    
    notes = TextAreaField("Notes / Observations",
                         render_kw={"placeholder": "What did you learn from this backtest?"})
    
    after_image = FileField("Chart Screenshot")
    
    submit = SubmitField("Save Backtest")

