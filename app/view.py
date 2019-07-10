from app import app
from flask import render_template, request
from forms import DownloadForm


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['POST', 'GET'])
def download():
    if request.method == 'POST':
        pass

    form = DownloadForm()
    return render_template('download.html', form=form)


@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

