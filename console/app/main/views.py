# coding: utf-8
from flask import render_template, redirect, url_for, jsonify, abort, request, flash, current_app
from flask_login import login_required

from . import main
from .forms import *
from ..base import Check
from ..app import upload_files
from config import Config
import os
from datetime import datetime


@main.route('/files', methods=['GET', 'POST'])
@login_required
def files():
    return render_template('main/files.html')
