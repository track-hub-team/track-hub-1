from app.modules.auth.models import User
from app.modules.community.models import Community, CommunityCurator
from core.seeders.BaseSeeder import BaseSeeder


class CommunitySeeder(BaseSeeder):
    priority = 10  # Run after auth (1) and dataset seeders

    def run(self):
        # Obtener usuarios existentes
        users = User.query.all()
        if len(users) < 1:
            print("Warning: Not enough users for community seeding. Skipping.")
            return

        user1 = users[0]
        user2 = users[1] if len(users) > 1 else users[0]

        # Crear 2 comunidades con logos en static/img/community/
        communities = [
            Community(
                name="Software Engineering Research",
                slug="software-engineering-research",
                description=(
                    "Community focused on software engineering and development methodologies. "
                    "This community brings together researchers and practitioners working on "
                    "software product lines, feature modeling, and variability management."
                ),
                logo_path="/static/img/community/software-engineering.png",
                creator_id=user1.id,
            ),
            Community(
                name="Machine Learning Models",
                slug="machine-learning-models",
                description=(
                    "Feature models for machine learning applications and AI systems. "
                    "Explore variability in ML pipelines, model configurations, and deployment strategies."
                ),
                logo_path="/static/img/community/machine-learning.png",
                creator_id=user2.id,
            ),
        ]

        seeded_communities = self.seed(communities)

        # Crear curadores (el creador es curador automáticamente)
        curators = []
        for community in seeded_communities:
            curators.append(
                CommunityCurator(
                    community_id=community.id,
                    user_id=community.creator_id,
                )
            )

        self.seed(curators)
