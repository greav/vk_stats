import vk_api
from flask import Flask
from .config import ACCESS_TOKEN

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

session = vk_api.VkApi(token=ACCESS_TOKEN)
vk = session.get_api()

from app import view
