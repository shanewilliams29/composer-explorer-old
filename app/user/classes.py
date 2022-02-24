from wtforms.validators import ValidationError
from flask_login import current_user
from google.cloud import storage
import requests
from flask import current_app
from PIL import Image
import io


class Unique(object):
    def __init__(self, model, field, message=u'This name is already taken.'):
        self.model = model
        self.field = field
        self.message = message

    def __call__(self, form, field):
        check = self.model.query.filter(self.field == field.data).first()
        if check and current_user.display_name != field.data:
            raise ValidationError(self.message)


def get_avatar(username, imgurl):

    try:
        response = requests.head(imgurl)
    except:
        return "Error: Invalid URL specified.", 403
    try:
        filetype = response.headers['content-type']
        filesize = float(response.headers['content-length']) / 5242880
    except:
        return "Error: Invalid image link.", 403

    if "image/jpeg" not in filetype and "image/png" not in filetype:
        return "Error: Link is not to a .jpg or .png file", 403

    if filesize > 5:
        return "Error: Image size is too large. Max size is 5 MB.", 403

    client = storage.Client(project='composer-explorer')
    bucket = client.get_bucket('composer-explorer.appspot.com')
    blob = bucket.blob('avatars/{}.jpg'.format(username))

    image = Image.open(requests.get(imgurl, stream=True).raw)
    image.thumbnail((200, 200))
    image = image.convert('RGB')

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    blob.cache_control = 'public, max-age=0'
    blob.upload_from_string(img_byte_arr, content_type='image/jpeg')

    return current_app.config['STATIC'] + 'avatars/{}.jpg'.format(username), 200


def upload_avatar(username, file):

    client = storage.Client(project='composer-explorer')
    bucket = client.get_bucket('composer-explorer.appspot.com')
    blob = bucket.blob('avatars/{}.jpg'.format(username))

    try:
        image = Image.open(file)
    except:
        return "Error: Invalid or no image file specified.", 403
    image.thumbnail((200, 200))
    image = image.convert('RGB')

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    blob.cache_control = 'public, max-age=0'
    blob.upload_from_string(img_byte_arr, content_type='image/jpeg')

    return current_app.config['STATIC'] + 'avatars/{}.jpg'.format(username), 200
