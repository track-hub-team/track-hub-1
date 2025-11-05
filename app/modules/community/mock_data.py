"""
Mock data for community module frontend development.
TODO: Remove this file when backend is ready and replace with real service calls.

Structure based on analysis of existing DataSet model and Community requirements.
See COMMUNITY_DATA_MODEL_ANALYSIS.md for details.
"""

# Mock users (curators and creators)
MOCK_USERS = {
    1: {"id": 1, "email": "creator1@uvlhub.io", "name": "John", "surname": "Doe"},
    2: {"id": 2, "email": "curator1@uvlhub.io", "name": "Jane", "surname": "Smith"},
    3: {"id": 3, "email": "curator2@uvlhub.io", "name": "Bob", "surname": "Johnson"},
    4: {"id": 4, "email": "creator2@uvlhub.io", "name": "Alice", "surname": "Williams"},
    5: {"id": 5, "email": "requester1@uvlhub.io", "name": "Charlie", "surname": "Brown"},
}

MOCK_COMMUNITIES = [
    {
        "id": 1,
        "name": "Software Engineering Research",
        "slug": "software-engineering-research",
        "description": (
            "Community focused on software engineering and development methodologies. "
            "This community brings together researchers and practitioners working on "
            "software product lines, feature modeling, and variability management."
        ),
        "logo_path": "https://via.placeholder.com/150/0066cc/ffffff?text=SE",
        "created_at": "2024-01-15",
        "updated_at": "2024-10-20",
        "creator_id": 1,
        "creator": MOCK_USERS[1],
        "curators": [MOCK_USERS[1], MOCK_USERS[2]],
        "datasets_count": 42,
    },
    {
        "id": 2,
        "name": "Machine Learning Models",
        "slug": "machine-learning-models",
        "description": (
            "Feature models for machine learning applications and AI systems. "
            "Explore variability in ML pipelines, model configurations, and deployment strategies."
        ),
        "logo_path": "https://via.placeholder.com/150/ff6600/ffffff?text=ML",
        "created_at": "2024-02-20",
        "updated_at": "2024-09-15",
        "creator_id": 4,
        "creator": MOCK_USERS[4],
        "curators": [MOCK_USERS[4], MOCK_USERS[3]],
        "datasets_count": 28,
    },
    {
        "id": 3,
        "name": "Automotive Systems",
        "slug": "automotive-systems",
        "description": (
            "Variability models for automotive software systems including ADAS, "
            "infotainment, and vehicle configuration models."
        ),
        "logo_path": "https://via.placeholder.com/150/009933/ffffff?text=AUTO",
        "created_at": "2024-03-10",
        "updated_at": "2024-08-22",
        "creator_id": 1,
        "creator": MOCK_USERS[1],
        "curators": [MOCK_USERS[1]],
        "datasets_count": 15,
    },
    {
        "id": 4,
        "name": "IoT and Embedded Systems",
        "slug": "iot-embedded-systems",
        "description": (
            "Internet of Things device configurations and embedded system variability models. "
            "Focus on resource-constrained environments and edge computing."
        ),
        "logo_path": "https://via.placeholder.com/150/9933cc/ffffff?text=IoT",
        "created_at": "2024-04-05",
        "updated_at": "2024-10-01",
        "creator_id": 2,
        "creator": MOCK_USERS[2],
        "curators": [MOCK_USERS[2], MOCK_USERS[3]],
        "datasets_count": 31,
    },
    {
        "id": 5,
        "name": "Cloud Computing",
        "slug": "cloud-computing",
        "description": (
            "Cloud infrastructure and service configuration models. "
            "Includes feature models for microservices, containerization, and cloud-native applications."
        ),
        "logo_path": "https://via.placeholder.com/150/cc3366/ffffff?text=CLOUD",
        "created_at": "2024-05-12",
        "updated_at": "2024-07-30",
        "creator_id": 4,
        "creator": MOCK_USERS[4],
        "curators": [MOCK_USERS[4]],
        "datasets_count": 19,
    },
    {
        "id": 6,
        "name": "Mobile Applications",
        "slug": "mobile-applications",
        "description": (
            "Feature models for mobile app development across iOS, Android, and cross-platform frameworks. "
            "Focus on app configuration and feature toggles."
        ),
        "logo_path": "https://via.placeholder.com/150/ff9900/ffffff?text=MOBILE",
        "created_at": "2024-06-18",
        "updated_at": "2024-09-05",
        "creator_id": 2,
        "creator": MOCK_USERS[2],
        "curators": [MOCK_USERS[2], MOCK_USERS[1]],
        "datasets_count": 23,
    },
]

# Mock pending requests
# NOTE: These reference REAL dataset IDs from the database
MOCK_PENDING_REQUESTS = [
    {
        "id": 101,
        "community_id": 1,
        "dataset_id": 1,
        "dataset": None,  # Will be populated from DB
        "requester_id": 5,
        "requester": MOCK_USERS[5],
        "message": (
            "This dataset fits perfectly with the community goals and contains valuable feature models. "
            "It would be a great addition to the Software Engineering Research community."
        ),
        "status": "pending",
        "requested_at": "2024-10-25",
        "reviewed_at": None,
        "reviewed_by": None,
        "review_comment": None,
    },
    {
        "id": 102,
        "community_id": 1,
        "dataset_id": 2,
        "dataset": None,
        "requester_id": 5,
        "requester": MOCK_USERS[5],
        "message": (
            "Collection of variability models that would benefit the research community "
            "studying software engineering methodologies."
        ),
        "status": "pending",
        "requested_at": "2024-10-26",
        "reviewed_at": None,
        "reviewed_by": None,
        "review_comment": None,
    },
    {
        "id": 103,
        "community_id": 2,
        "dataset_id": 3,
        "dataset": None,
        "requester_id": 5,
        "requester": MOCK_USERS[5],
        "message": (
            "Feature models representing software product line variability. "
            "Relevant for ML-based analysis and recommendation systems."
        ),
        "status": "pending",
        "requested_at": "2024-10-28",
        "reviewed_at": None,
        "reviewed_by": None,
        "review_comment": None,
    },
    {
        "id": 104,
        "community_id": 4,
        "dataset_id": 4,
        "dataset": None,
        "requester_id": 5,
        "requester": MOCK_USERS[5],
        "message": (
            "IoT and embedded systems dataset that aligns with the community focus "
            "on resource-constrained environments."
        ),
        "status": "pending",
        "requested_at": "2024-10-29",
        "reviewed_at": None,
        "reviewed_by": None,
        "review_comment": None,
    },
]
