import os
import shutil
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.modules.auth.models import User
from app.modules.dataset.models import Author, DSMetaData, DSMetrics, GPXDataset, PublicationType, UVLDataset
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.hubfile.models import Hubfile
from core.seeders.BaseSeeder import BaseSeeder


class DataSetSeeder(BaseSeeder):

    priority = 2  # Lower priority

    def run(self):
        # Retrieve users
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()

        if not user1 or not user2:
            raise Exception("Users not found. Please seed users first.")

        # Create DSMetrics instance
        ds_metrics = DSMetrics(number_of_models="5", number_of_features="50")
        seeded_ds_metrics = self.seed([ds_metrics])[0]

        # Create DSMetaData instances
        ds_meta_data_list = [
            DSMetaData(
                deposition_id=1 + i,
                title=f"Sample dataset {i+1}",
                description=f"Description for dataset {i+1}",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi=f"10.1234/dataset{i+1}",
                dataset_doi=f"10.1234/dataset{i+1}",
                tags="tag1, tag2",
                ds_metrics_id=seeded_ds_metrics.id,
            )
            for i in range(4)
        ]
        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        # Create Author instances and associate with DSMetaData
        authors = [
            Author(
                name=f"Author {i+1}",
                affiliation=f"Affiliation {i+1}",
                orcid=f"0000-0000-0000-000{i}",
                ds_meta_data_id=seeded_ds_meta_data[i % 4].id,
            )
            for i in range(4)
        ]
        self.seed(authors)

        # Create UVLDataset instances
        datasets = [
            UVLDataset(
                user_id=user1.id if i % 2 == 0 else user2.id,
                ds_meta_data_id=seeded_ds_meta_data[i].id,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(4)
        ]
        seeded_datasets = self.seed(datasets)

        # Assume there are 12 UVL files, create corresponding FMMetaData and FeatureModel
        fm_meta_data_list = [
            FMMetaData(
                filename=f"file{i+1}.uvl",
                title=f"Feature Model {i+1}",
                description=f"Description for feature model {i+1}",
                publication_type=PublicationType.SOFTWARE_DOCUMENTATION,
                publication_doi=f"10.1234/fm{i+1}",
                tags="tag1, tag2",
                file_version="1.0",
            )
            for i in range(12)
        ]
        seeded_fm_meta_data = self.seed(fm_meta_data_list)

        # Create Author instances and associate with FMMetaData
        fm_authors = [
            Author(
                name=f"Author {i+5}",
                affiliation=f"Affiliation {i+5}",
                orcid=f"0000-0000-0000-000{i+5}",
                fm_meta_data_id=seeded_fm_meta_data[i].id,
            )
            for i in range(12)
        ]
        self.seed(fm_authors)

        feature_models = [
            FeatureModel(data_set_id=seeded_datasets[i // 3].id, fm_meta_data_id=seeded_fm_meta_data[i].id)
            for i in range(12)
        ]
        seeded_feature_models = self.seed(feature_models)

        # Create files, associate them with FeatureModels and copy files
        load_dotenv()
        working_dir = os.getenv("WORKING_DIR", "")
        src_folder = os.path.join(working_dir, "app", "modules", "dataset", "uvl_examples")
        for i in range(12):
            file_name = f"file{i+1}.uvl"
            feature_model = seeded_feature_models[i]
            dataset = next(ds for ds in seeded_datasets if ds.id == feature_model.data_set_id)
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            uvl_file = Hubfile(
                name=file_name,
                checksum=f"checksum{i+1}",
                size=os.path.getsize(file_path),
                feature_model_id=feature_model.id,
            )
            self.seed([uvl_file])

        # Create GPX datasets
        gpx_ds_metrics = DSMetrics(number_of_models="5", number_of_features="0")
        seeded_gpx_ds_metrics = self.seed([gpx_ds_metrics])[0]

        # Create GPX DSMetaData instances
        gpx_ds_meta_data_list = [
            DSMetaData(
                deposition_id=100 + i,
                title=f"GPS Track Collection {i+1}",
                description=f"Collection of GPS tracks for outdoor activities - Dataset {i+1}",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi=f"10.1234/gpx_dataset{i+1}",
                dataset_doi=f"10.1234/gpx_dataset{i+1}",
                tags="gps, tracks, outdoor, hiking",
                ds_metrics_id=seeded_gpx_ds_metrics.id,
            )
            for i in range(2)
        ]
        seeded_gpx_ds_meta_data = self.seed(gpx_ds_meta_data_list)

        # Create GPX Authors
        gpx_authors = [
            Author(
                name=f"GPS Tracker {i+1}",
                affiliation=f"Outdoor Association {i+1}",
                orcid=f"0000-0000-0000-010{i}",
                ds_meta_data_id=seeded_gpx_ds_meta_data[i].id,
            )
            for i in range(2)
        ]
        self.seed(gpx_authors)

        # Create GPX Dataset instances
        gpx_datasets = [
            GPXDataset(
                user_id=user1.id if i == 0 else user2.id,
                ds_meta_data_id=seeded_gpx_ds_meta_data[i].id,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(2)
        ]
        seeded_gpx_datasets = self.seed(gpx_datasets)

        # Create GPX FeatureModels and files
        gpx_fm_meta_data_list = [
            FMMetaData(
                filename=f"file{i+1}.gpx",
                title=f"GPS Track {i+1}",
                description=f"GPS track recording {i+1}",
                publication_type=PublicationType.OTHER,
                publication_doi=f"10.1234/gpx_track{i+1}",
                tags="gps, track",
                file_version="1.0",
            )
            for i in range(5)
        ]
        seeded_gpx_fm_meta_data = self.seed(gpx_fm_meta_data_list)

        # Create GPX FeatureModels
        gpx_feature_models = [
            FeatureModel(
                data_set_id=seeded_gpx_datasets[0].id if i < 3 else seeded_gpx_datasets[1].id,
                fm_meta_data_id=seeded_gpx_fm_meta_data[i].id,
            )
            for i in range(5)
        ]
        seeded_gpx_feature_models = self.seed(gpx_feature_models)

        # Copy GPX files and create Hubfile entries
        gpx_src_folder = os.path.join(working_dir, "app", "modules", "dataset", "gpx_examples")
        for i in range(5):
            file_name = f"file{i+1}.gpx"
            feature_model = seeded_gpx_feature_models[i]
            dataset = next(ds for ds in seeded_gpx_datasets if ds.id == feature_model.data_set_id)
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(gpx_src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            gpx_file = Hubfile(
                name=file_name,
                checksum=f"gpx_checksum{i+1}",
                size=os.path.getsize(file_path),
                feature_model_id=feature_model.id,
            )
            self.seed([gpx_file])
