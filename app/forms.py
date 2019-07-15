from wtforms import Form, IntegerField, BooleanField, RadioField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired


class DownloadForm(Form):
    id_ = IntegerField('ID', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    post_id_checked = BooleanField('Post ID')
    text_checked = BooleanField('Text')
    attachments_checked = BooleanField('Attachments')
    n_attachments_checked = BooleanField('Number of attachments')
    n_likes_checked = BooleanField('Number of likes')
    n_reposts_checked = BooleanField('Number of reposts')
    n_comments_checked = BooleanField('Number of comments')


class StatisticsForm(Form):
    id_ = IntegerField('ID', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    radio = RadioField('Label', choices=[('hour', 'by hours'), ('dow', 'by days of week'), ('month', 'by months'),
                                         ('year', 'by years')], default='hour')
