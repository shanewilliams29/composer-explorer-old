from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField


class ClearComposer(FlaskForm):
    composer = StringField('Delete COMPOSER Records')
    work = StringField('Delete WORK Records')
    album = StringField('Delete ALBUM Records')
    submit = SubmitField('Delete')


class FillAlbums(FlaskForm):
    work = StringField('Work ID')
    album = StringField('Spotify Album ID')
    submit = SubmitField('Fill Tracks')


class SpotifyAdd(FlaskForm):
    composer = StringField('Composer')
    uri = StringField('Album URI')
    trackno = StringField('Track number')
    position = StringField('Position (ms)')
    submit = SubmitField('Submit')


class AddAlbum(FlaskForm):
    workid = StringField('Work ID')
    uri = StringField('Album ID')
    submit = SubmitField('Submit')


class SumAlbums(FlaskForm):
    composer = StringField('Composer Short Name')
    submit = SubmitField('Submit')


class NullForm(FlaskForm):
    "Cake"
    pass
