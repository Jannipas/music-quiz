"""WSGI entrypoint for gunicorn / Cloud Run.

The application lives in ``music-quiz.py``. Because that filename contains a
hyphen it is not a valid Python module name, so gunicorn cannot import it as
``music-quiz:app`` directly. This shim loads it by file path and exposes ``app``.

It also wraps the app in ProxyFix so that behind the Cloud Run HTTPS proxy
(which forwards requests over HTTP with an ``X-Forwarded-Proto`` header) Flask
correctly reports requests as secure. Without this, ``Talisman(force_https=True)``
in production would redirect-loop.
"""

import importlib.util
import os

from werkzeug.middleware.proxy_fix import ProxyFix

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "music_quiz", os.path.join(_here, "music-quiz.py")
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
