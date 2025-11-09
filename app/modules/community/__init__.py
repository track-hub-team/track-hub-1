from core.blueprints.base_blueprint import BaseBlueprint

community_bp = BaseBlueprint("community", __name__, template_folder="templates")

# Import routes and API to register them with the blueprint
from app.modules.community import api, models, routes  # noqa: F401, E402
