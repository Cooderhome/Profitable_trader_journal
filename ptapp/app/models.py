from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db
from datetime import datetime, date

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = db.relationship('Subscription', backref='user', uselist=False)

    @property
    def is_pro(self):
        # Default to False if no subscription record or not active/pro
        return self.subscription is not None and \
               self.subscription.plan_type == 'pro' and \
               self.subscription.is_active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_type = db.Column(db.String(20), default='free') # free, pro
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    next_billing_date = db.Column(db.DateTime)

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # KPI Boolean Flags
    journal_complete = db.Column(db.Boolean, default=False)
    rules_followed = db.Column(db.Boolean, default=False)
    news_checked = db.Column(db.Boolean, default=False)
    

    # Before trade
    pair = db.Column(db.String(20))
    direction = db.Column(db.String(10))  # buy/sell
    entry_price = db.Column(db.Float)
    risk_amount = db.Column(db.Float) # Actual dollar risk taken
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    lot_size = db.Column(db.Float)
    pre_trade_analysis = db.Column(db.Text)
    before_image = db.Column(db.String(200))  # path to uploaded image

    # After trade
    result = db.Column(db.String(20))  # win/loss/break-even
    profit_loss = db.Column(db.Float)
    reflection = db.Column(db.Text)
    mistakes = db.Column(db.Text)
    after_image = db.Column(db.String(200))  # path to uploaded image

    start_balance = db.Column(db.Float, nullable=True) # e.g. 26.3
    
    # New Analysis Fields
    strategy = db.Column(db.String(100))
    risk_reward = db.Column(db.Float)
    news_event = db.Column(db.String(100)) # e.g. "NFP", "None"
    ai_confidence = db.Column(db.Float) # 0.0 to 1.0
    
    # Link to a specific Growth Plan/Goal
    trading_goal_id = db.Column(db.Integer, db.ForeignKey('trading_goals.id'), nullable=True)

class BacktestEntry(db.Model):
    __tablename__ = 'backtest_entries'
    id = db.Column(db.Integer, primary_key=True)
    pair=  db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    strategy_name = db.Column(db.String(200))
    entry_time = db.Column(db.DateTime)
    exit_time = db.Column(db.DateTime)
    entry_price = db.Column(db.Float)
    exit_price = db.Column(db.Float)
    result = db.Column(db.String(10))  # win/loss
    notes = db.Column(db.Text)
    image_filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Backtest {self.strategy_name} {self.result}>"

class Planner(db.Model):
    __tablename__ = 'planners'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    
    # Trading Plan Details
    pair = db.Column(db.String(20))  # e.g., XAUUSD
    direction = db.Column(db.String(10))  # buy/sell
    entry_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    risk_amount = db.Column(db.Float)
    strategy = db.Column(db.String(100))  # e.g., "Breakout Strategy"
    
    # Plan Description
    goal = db.Column(db.String(255))  # What you want to achieve today
    analysis = db.Column(db.Text)  # Pre-trade analysis/reasoning
    
    # Execution Tracking
    completed = db.Column(db.Boolean, default=False)
    executed_trade_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True)
    
    # Reflection
    reflection = db.Column(db.Text)  # Did you follow the plan?
    
    # Legacy field for backward compatibility
    tasks = db.Column(db.Text)

    def __repr__(self):
        return f"<Planner {self.date} - {self.pair or self.goal}>"

class KPISummary(db.Model):
    __tablename__ = 'kpi_summaries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    week_start = db.Column(db.Date)
    journaling_score = db.Column(db.Float, default=0.0)
    backtest_score = db.Column(db.Float, default=0.0)
    risk_score = db.Column(db.Float, default=0.0)
    execution_score = db.Column(db.Float, default=0.0)
    discipline_score = db.Column(db.Float, default=0.0)
    total_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TradingGoal(db.Model):
    __tablename__ = 'trading_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g. "Buy a Phone"
    target_amount = db.Column(db.Float, nullable=False) # e.g. 160
    start_balance = db.Column(db.Float, nullable=False) # e.g. 26.3
    
    # Strategy Params for Projection
    win_rate = db.Column(db.Float, default=50.0) # e.g. 72
    risk_per_trade = db.Column(db.Float, default=10.0) # e.g. 5
    reward_per_trade = db.Column(db.Float, default=20.0) # e.g. 12.5
    lot_size = db.Column(db.Float, default=0.01)
    
    start_date = db.Column(db.Date, default=datetime.utcnow)
    deadline = db.Column(db.Date)
    
    status = db.Column(db.String(20), default='active') # active, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def current_profit(self, current_balance):
        return current_balance - self.start_balance

    def progress(self, current_balance_profit):
        if self.target_amount <= 0: return 0
        return min(100.0, (current_balance_profit / self.target_amount) * 100)
