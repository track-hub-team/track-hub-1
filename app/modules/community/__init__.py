from core.blueprints.base_blueprint import BaseBlueprint

community_bp = BaseBlueprint("community", __name__, template_folder="templates")

from app.modules.community import models, routes  # noqa: F401, E402
