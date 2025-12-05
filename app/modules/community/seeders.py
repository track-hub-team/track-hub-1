from app.modules.auth.models import User
from app.modules.community.models import Community, CommunityCurator, CommunityDataset
from app.modules.dataset.models import GPXDataset
from core.seeders.BaseSeeder import BaseSeeder


class CommunitySeeder(BaseSeeder):
    priority = 10

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

        # Crear curadores
        curators = []
        for community in seeded_communities:
            curators.append(
                CommunityCurator(
                    community_id=community.id,
                    user_id=community.creator_id,
                )
            )

        self.seed(curators)

        # Vincular datasets GPX a las comunidades
        gpx_datasets = GPXDataset.query.all()
        if len(gpx_datasets) >= 2:
            # Vincular GPX datasets a la primera comunidad (Software Engineering Research)
            community_datasets = [
                CommunityDataset(
                    community_id=seeded_communities[0].id,
                    dataset_id=gpx_datasets[0].id,
                    added_by_id=user1.id,
                ),
                # Vincular a la segunda comunidad (Machine Learning Models)
                CommunityDataset(
                    community_id=seeded_communities[1].id,
                    dataset_id=gpx_datasets[1].id,
                    added_by_id=user2.id,
                ),
            ]
            self.seed(community_datasets)
        else:
            print("Warning: Not enough GPX datasets found for community seeding.")
