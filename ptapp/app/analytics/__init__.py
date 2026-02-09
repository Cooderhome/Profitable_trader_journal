from flask import Blueprint

analytics_bp = Blueprint('analytics', __name__, template_folder='../templates')

from . import routes
