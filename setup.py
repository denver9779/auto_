import setuptools
import textwrap
from setuptools import find_packages

if __name__ == '__main__':
    setuptools.setup(
        name="filling",
        version="1.0.0",
        description="auto_filling",
        author="jason",
        author_email="jason@gmail.com",
        long_description=textwrap.dedent("""auto_filling"""),
        packages=find_packages(),
        install_requires=[
            "alembic",
            "Babel",
            "click",
            "cssmin",
            "dominate",
            "Flask",
            "Flask-Assets",
            "Flask-Babel",
            "Flask-Bootstrap",
            "Flask-Login",
            "Flask-Migrate",
            "Flask-Moment",
            "Flask-Script",
            "Flask-SQLAlchemy",
            "Flask-Uploads",
            "Flask-WTF",
            "itsdangerous",
            "Jinja2",
            "jsmin",
            "Mako",
            "MarkupSafe",
            "PyMySQL",
            "python-dateutil",
            "python-editor",
            "pytz",
            "six",
            "SQLAlchemy",
            "visitor",
            "webassets",
            "Werkzeug",
            "WTForms"
        ],
        include_package_data=True,
        zip_safe=False,
    )
