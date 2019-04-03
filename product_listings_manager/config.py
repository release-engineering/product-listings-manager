"""PLM configuration module."""
import os


class Config(object):
    """Default config."""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/compose'


class DevConfig(Config):
    """Development config."""
    SQLALCHEMY_ECHO = True


def load_config(app):
    app.config.from_object('product_listings_manager.config.Config')
    app.config.from_pyfile('/etc/product-listings-manager/config.py', silent=True)

    if app.debug:
        app.config.from_object('product_listings_manager.config.DevConfig')

    app.config.from_envvar('PLM_CONFIG_FILE', silent=True)

    # It's convenient to overwrite default config via env var in container.
    if os.getenv('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
