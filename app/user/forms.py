from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, RadioField, FileField
from wtforms.validators import ValidationError, DataRequired, Length
from app.models import User
from app.user.classes import Unique


class EditProfileForm(FlaskForm):
    display_name = StringField('Display Name', validators=[DataRequired(), Length(min=0, max=64), Unique(User, User.display_name)])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')


class ClearVisits(FlaskForm):
    submit = SubmitField('Clear all Visited Works')


class ChangeAvatar(FlaskForm):
    choice = RadioField('Change Profile Picture', choices=[('remove', 'Remove photo'), ('restore', 'Restore Spotify photo'), ('upload', 'Upload image')], default='upload')
    link = StringField('Option 1: Paste URL to image', description='Must be a .jpg or .png file smaller than 5 MB.', validators=[Length(min=0, max=2064)])
    file = FileField('Option 2: Upload an image from device', description='Must be a .jpg or .png file smaller than 5 MB.', validators=[Length(min=0, max=2064)])
    submit = SubmitField('Submit')


class MessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[
        DataRequired(), Length(min=0, max=1400)])
    submit = SubmitField('Submit')
