"""
Django settings for phylobot project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from os import listdir, environ
from django.core.exceptions import ImproperlyConfigured
def get_env_variable(var_name):
    """Get the env. variable, or return exception"""
    try:
        return environ[var_name]
    except KeyError:
        import getpass
        curr_username = getpass.getuser()
        error_msg = "Set the {} environment variable for user {}".format(var_name, curr_username)
        raise ImproperlyConfigured(error_msg)
                                   

#configure()
                                   
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SETTINGS_DIR = os.path.dirname(__file__)
PROJECT_PATH = os.path.join(SETTINGS_DIR, os.pardir)
PROJECT_PATH = os.path.abspath(PROJECT_PATH)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

""" stuff for django-allauth"""
TEMPLATE_CONTEXT_PROCESSORS = (
    # Required by allauth template tags
    "django.core.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    # allauth specific context processors
    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",
)
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)
ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = False
LOGIN_REDIRECT_URL = '/portal/'
SOCIALACCOUNT_QUERY_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAY = 3
ACCOUNT_SIGNUP_PASSWORD_VERIFICATION = True
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION  = True

"""Amazon SES"""
EMAIL_BACKEND = get_env_variable("EMAIL_BACKEND") #'django_ses.SESBackend'
AWS_SES_REGION_NAME = get_env_variable("SES_REGION") #'us-west-2'
EMAIL_HOST = get_env_variable("EMAIL_HOST") #'email-smtp.us-west-2.amazonaws.com'
EMAIL_PORT = get_env_variable("EMAIL_PORT") #465
DEFAULT_FROM_EMAIL =  get_env_variable("DEFAULT_FROM_EMAIL") #'hello@phylobot.com'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

#STATIC_PATH = os.path.join(PROJECT_PATH,'static')
#STATIC_URL = '/static/'
#STATICFILES_DIRS= (STATIC_PATH,)
#MEDIA_URL = '/media/'
#MEDIA_ROOT = os.path.join(STATIC_PATH, "media") 
#STATIC_MEDIA_URL = STATIC_URL + MEDIA_URL

########## STATIC FILE CONFIGURATION
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = '/home/ubuntu/phylobot-django/phylobot/static'
STATIC_URL = '/static/'

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MEDIA_ROOT = os.path.join(STATIC_ROOT, 'media')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END STATIC FILE CONFIGURATION



# URL of the login page.
from django.core.urlresolvers import reverse_lazy
LOGIN_URL = 'allauth.account.login'

AUTH_PROFILE_MODULE = 'phylobot.UserProfile'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable("PHYLOBOT_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = True

#ALLOWED_HOSTS = []
ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #'django.contrib.humanize' # this app "humanizes" dates, and some nuimbers: https://docs.djangoproject.com/en/1.7/ref/contrib/humanize/
    'phylobot',
    'portal',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_ses',
)
SITE_ID = 1

ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_AUTO_LOGIN = True

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'phylobot.urls'

WSGI_APPLICATION = 'phylobot.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True



