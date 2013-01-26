from distutils.core import setup
setup( name         = 'FAS-OpenID'
     , version      = file('VERSION').read()
     , author       = 'Patrick Uiterwijk'
     , author_email = 'puiterwijk@fedoraproject.org'
     , py_modules   = ['fas_openid']
     )
