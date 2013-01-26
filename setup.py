from setuptools import setup, find_packages

setup( name                 = 'FAS-OpenID'
     , version              = file('VERSION').read()
     , author               = 'Patrick Uiterwijk'
     , author_email         = 'puiterwijk@fedoraproject.org'
     , packages             = find_packages()
     , zip_safe             = False
     , include_package_data = True
     , install_requires     = ['Flask']
     )
