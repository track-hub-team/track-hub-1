from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class CommunityForm(FlaskForm):
    """Form for creating or editing a community"""

    name = StringField(
        "Community Name",
        validators=[
            DataRequired(message="Community name is required"),
            Length(min=3, max=200, message="Name must be between 3 and 200 characters"),
        ],
        render_kw={"placeholder": "e.g., Software Engineering Research"},
    )

    description = TextAreaField(
        "Description",
        validators=[
            DataRequired(message="Description is required"),
            Length(min=20, max=2000, message="Description must be between 20 and 2000 characters"),
        ],
        render_kw={"placeholder": "Describe the purpose and scope of this community...", "rows": 5},
    )

    logo = FileField(
        "Community Logo",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "gif"], "Only image files are allowed (jpg, jpeg, png, gif)"),
        ],
    )

    submit = SubmitField("Create Community")


class ProposeDatasetForm(FlaskForm):
    """Form for proposing a dataset to a community"""

    dataset_id = SelectField(
        "Select Dataset",
        coerce=int,
        validators=[DataRequired(message="Please select a dataset")],
        render_kw={"class": "form-select"},
    )

    message = TextAreaField(
        "Message to Curators",
        validators=[Optional(), Length(max=1000, message="Message must be less than 1000 characters")],
        render_kw={"placeholder": "Explain why this dataset fits this community (optional)...", "rows": 4},
    )

    submit = SubmitField("Submit Proposal")
