from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, JWTManager
from sqlalchemy import text, Date
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import bcrypt
import json
import os
from sqlalchemy.ext.automap import automap_base
import requests
import uuid
from datetime import datetime, timedelta
import zoneinfo
import tzlocal
import pymysql
from dotenv import load_dotenv
import sys
from pathlib import Path
import logging
from typing import Dict, Optional
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from interface import CHESSInterface
from threading import Lock
import time
import yaml
from translator import SQLTranslator
import re


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# SQLite database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
pwd = os.getenv("DB_PASSWORD")
dbip = os.getenv("DB_IP")
username = os.getenv("DB_USERNAME")

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{username}:{pwd}@{dbip}/wtl_employee_tracker"  # Change to SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'dkhfkasdhkjvhxcvhueh439erd7fy87awye79yr79'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=3)
db = SQLAlchemy(app)
jwt = JWTManager(app)  # Initialize JWT manager


# class SessionRequest(BaseModel):
#     db_name: str = "wtl_employee_tracker"  # Default database name

# class QueryRequest(BaseModel):
#     prompt: str
#     session_id: str  # Frontend must provide the session ID from /create_session
#     user_id: str = "default"  # Make user_id optional with a default value

class Users(db.Model):
    __tablename__ = 'users'
    uuid = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    employee_id = db.Column(db.String(36), db.ForeignKey('employee.uuid'), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Employee(db.Model):
    __tablename__ = 'employee'
    uuid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(255), nullable=True)
    alias = db.Column(db.String(255), nullable=True)
    position = db.Column(db.Text, nullable=True)
    subdepartment = db.Column(db.String(255), nullable=True)

class Project(db.Model):
    __tablename__ = 'project'
    uuid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    team_id = db.Column(db.String(36), db.ForeignKey('team.uuid'), nullable=True)
    address = db.Column(db.Text, nullable=True)
    project_type = db.Column('type', db.String(100), nullable=True)  # Renamed to avoid Python keyword
    area = db.Column(db.Float, nullable=True)
    sign_date = db.Column(db.Date, nullable=True)
    expected_completion_date = db.Column(db.Date, nullable=True)
    revenue = db.Column(db.Numeric(15, 2), nullable=True)
    revenue_note = db.Column(db.Text, nullable=True)
    client_id = db.Column(db.String(36), nullable=True)

class WorkHour(db.Model):
    __tablename__ = 'work_hour'
    uuid = db.Column(db.String(36), primary_key=True)
    is_reversed = db.Column(db.Boolean, default=False)
    task_description = db.Column(db.Text, nullable=True)
    is_standardized = db.Column(db.Boolean, default=True)
    project_id = db.Column(db.String(36), db.ForeignKey('project.uuid'), nullable=True)
    employee_id = db.Column(db.String(36), db.ForeignKey('employee.uuid'), nullable=True)
    hour = db.Column(db.Numeric(10, 2), nullable=True)
    start_date = db.Column(Date, nullable=True)
    end_date = db.Column(Date, nullable=True)

class Team(db.Model):
    __tablename__ = 'team'
    uuid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

class TeamAssignment(db.Model):
    __tablename__ = 'team_assignment'
    uuid = db.Column(db.String(36), primary_key=True)
    team_id = db.Column(db.String(36), db.ForeignKey('team.uuid'), nullable=True)
    employee_id = db.Column(db.String(36), db.ForeignKey('employee.uuid'), nullable=True)

class Client(db.Model):
    __tablename__ = 'client'
    uuid = db.Column(db.String(36), primary_key=True)
    source = db.Column(db.String(255), nullable=True)
    company = db.Column(db.String(255), nullable=True)
    contact = db.Column(db.String(255), nullable=True)
    background = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)


query_masks = {
        "level_1": """
        WITH 
        employee AS (
            SELECT * FROM employee
            WHERE uuid = :employee_id
        ),
        team_assignment AS (
            SELECT * FROM team_assignment
            WHERE employee_id = :employee_id
        ),
        team AS (
            SELECT * FROM team
            WHERE uuid IN (
                SELECT team_id FROM team_assignment
            )
        ),
        project AS (
            SELECT * FROM project
            WHERE team_id IN (
                SELECT team_id FROM team_assignment
            )
        ),
        client AS (
            SELECT * FROM client
            WHERE uuid IN (
                SELECT client_id FROM project
            )
        )
        """,
        "level_2": """
        WITH 
        employee AS (
            SELECT * FROM employee
            WHERE uuid IN (
                SELECT employee_id
                FROM team_assignment
                WHERE team_id IN (
                    SELECT team_id
                    FROM team_assignment
                    WHERE employee_id = :employee_id
                )
            )
        ),
        team_assignment AS (
            SELECT * FROM team_assignment
            WHERE team_id IN (
                SELECT team_id
                FROM team_assignment
                WHERE employee_id = :employee_id
            )
        ),
        team AS (
            SELECT * FROM team
            WHERE uuid IN (
                SELECT team_id FROM team_assignment
            )
        ),
        project AS (
            SELECT * FROM project
            WHERE team_id IN (
                SELECT team_id FROM team_assignment
            )
        ),
        client AS (
            SELECT * FROM client
            WHERE uuid IN (
                SELECT client_id FROM project
            )
        )
        """,
        "level_3": """
        WITH 
        employee AS (
            SELECT * FROM employee
            WHERE department = (
                SELECT department
                FROM employee
                WHERE uuid = :employee_id
            )
        ),
        team_assignment AS (
            SELECT * FROM team_assignment
            WHERE employee_id IN (
                SELECT uuid FROM employee
            )
        ),
        team AS (
            SELECT * FROM team
            WHERE uuid IN (
                SELECT team_id FROM team_assignment
            )
        ),
        project AS (
            SELECT * FROM project
            WHERE team_id IN (
                SELECT team_id FROM team_assignment
            )
        ),
        client AS (
            SELECT * FROM client
            WHERE uuid IN (
                SELECT client_id FROM project
            )
        )
        """,
        "level_4": """WITH _ AS (SELECT 1)"""  # Admin sees all
    }
    
def distribute_project_no_commit(employee_id, actual_hour, start_date, end_date, db):
    data_hour = db.session.execute(text("SELECT SUM(work_hour.hour) AS hour FROM work_hour WHERE start_date >= :start_date AND end_date <= :end_date GROUP BY employee_id HAVING employee_id = :id"), {"id": employee_id, 'start_date': start_date, 'end_date': end_date}).fetchone()
    if not data_hour:
        data_hour = 0
    else:
        data_hour = float(data_hour.hour)
    if data_hour >= actual_hour:
        return {"hour_diff": 0, "projects": []}
    else:
        diff_hour = actual_hour - data_hour
        if diff_hour < actual_hour / 5:
            return {'hour_diff': diff_hour, 'projects':[]}
        all_proj = db.session.execute(text("SELECT DISTINCT project_id, project.name AS name FROM work_hour JOIN project ON project_id = project.uuid WHERE start_date >=:start_date AND end_date <= :end_date"), {"start_date": start_date, 'end_date': end_date})
        all_proj_id = [(row.project_id, row.name) for row in all_proj]
        for row in all_proj_id:
            _id = row[0]
            err_handling_hour = diff_hour / len(all_proj_id)
            err_dict = {"employee_id": employee_id, "hour": err_handling_hour, "project_id": _id, "start_date": start_date, 'is_reversed': False, 'is_standardized': False, 'end_date': end_date, 'stage': '6. 其它', 'task_description': '错误的工时录入，多余工时平均计入全部项目。'}
            db.session.execute(text("INSERT INTO work_hour (uuid, employee_id, project_id, start_date, end_date, is_reversed, is_standardized, task_description, hour, stage) VALUES (UUID(), :employee_id, :project_id, :start_date, :end_date, :is_reversed, :is_standardized, :task_description, :hour, :stage)"), err_dict)
        return {"hour_diff": diff_hour, "projects": [x[1] for x in all_proj_id]}