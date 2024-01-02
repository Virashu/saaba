from saaba import App
from saaba.utils import get_path

PATH = get_path(__file__)

app = App()

app.static("/", PATH + "/")

app.listen("0.0.0.0", 8888, lambda: print("http://127.0.0.1:8888"))
