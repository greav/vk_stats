from wtforms import Form, IntegerField, BooleanField
from wtforms.fields.html5 import DateField


class DownloadForm(Form):
    user_id = IntegerField('User ID')
    date = DateField('Date')
    post_id_checked = BooleanField('Post ID')
    text_checked = BooleanField('Text')
    attachments_checked = BooleanField('Attachments')
    n_attachments_checked = BooleanField('Number of attachments')
    n_likes_checked = BooleanField('Number of likes')
    n_reposts_checked = BooleanField('Number of reposts')
    n_comments_checked = BooleanField('Number of comments')



