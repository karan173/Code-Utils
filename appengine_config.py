def webapp_add_wsgi_middleware(app):
  from google.appengine.ext.appstats import recording
  import sys
  sys.path.insert(0, 'libs') #added as recommended on https://developers.google.com/appengine/docs/python/tools/appstats
  app = recording.appstats_wsgi_middleware(app)
  return app