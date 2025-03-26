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
from datetime import datetime, timedelta, date
import zoneinfo
import tzlocal
import pymysql
import pandas as pd
from dotenv import load_dotenv
import sys
from pathlib import Path
import logging
from typing import Dict, Optional
import uuid
from pydantic import BaseModel
from interface import CHESSInterface
from threading import Lock
import yaml
import re
from decimal import Decimal

current_dir = Path(__file__).parent
src_dir = str(current_dir / "src")
sys.path.append(src_dir)

from data_structure import *


# Initialize interface
user_interfaces: Dict[str, CHESSInterface] = {}
interfaces_lock = Lock()

# Store active sessions
active_sessions: Dict[str, str] = {}  # Maps frontend_session_id to chess_session_id
sessions_lock = Lock()


# @app.before_request
# def refresh_login():
#     db.session.execute(text('PRAGMA foreign_keys=ON'))


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


# Login route
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = Users.query.filter_by(username=data['username']).first()
    if user and bcrypt.checkpw(data['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        identity = json.dumps({'employee_id': str(user.employee_id), 'role': str(user.role)})
        access_token = create_access_token(identity=identity)
        return jsonify({'access_token': access_token, 'level': str(user.role)}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/list', methods=['GET'])
@jwt_required()
def listReport():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    full_query = "SELECT work_hour.uuid AS uuid, name, task_description, hour, is_reversed, is_standardized, start_date, end_date FROM work_hour LEFT JOIN project ON project.uuid = work_hour.project_id WHERE work_hour.employee_id = :employee_id"
    try:
        result = db.session.execute(text(full_query), {"employee_id": employee_id})
        return jsonify([row._asdict() for row in result])
    except Exception as _:
        print(_)
        return "query execution failed", 500

@app.route('/list_individual', methods=['POST'])
@jwt_required()
def listReport_individ():
    user_identity = json.loads(get_jwt_identity())
    employee = request.json.get('name')
    full_query = "SELECT work_hour.uuid AS uuid, project.name, task_description, hour, is_reversed, is_standardized, start_date, end_date FROM work_hour LEFT JOIN project ON project.uuid = work_hour.project_id JOIN employee ON employee.uuid = work_hour.employee_id WHERE employee.name = :name"
    try:
        result = db.session.execute(text(full_query), {"name": employee})
        return jsonify([row._asdict() for row in result])
    except Exception as _:
        print(_)
        return "query execution failed", 500


# @app.route('/list_dept', methods=['GET'])
# @jwt_required()
# def listReport_dept():
#     user_identity = json.loads(get_jwt_identity())
#     employee_id = user_identity['employee_id']
#     role = user_identity['role']
    
#     # Calculate last week's date range
#     today = date.today()
#     last_monday = today - timedelta(days=today.weekday() + 7)
#     last_sunday = last_monday + timedelta(days=6)
    
#     # First get all employees in the department
#     dept_employees_query = """
#         SELECT e.uuid, e.name, e.position, e.subdepartment
#         FROM employee e 
#         WHERE e.department = (
#             SELECT department 
#             FROM employee 
#             WHERE uuid = :employee_id
#         )
#         ORDER BY e.subdepartment, e.name
#     """
    
#     # Then get work hours for last week
#     work_hours_query = """
#         SELECT 
#             e.uuid as employee_id,
#             e.name as employee_name,
#             SUM(wh.hour) as total_hours,
#             GROUP_CONCAT(DISTINCT p.name SEPARATOR ', ') as projects,
#             MIN(wh.start_date) as earliest_date,
#             MAX(wh.end_date) as latest_date
#         FROM employee e
#         LEFT JOIN work_hour wh ON e.uuid = wh.employee_id 
#             AND wh.start_date >= :start_date 
#             AND wh.start_date <= :end_date
#         LEFT JOIN project p ON wh.project_id = p.uuid
#         WHERE e.department = (
#             SELECT department 
#             FROM employee 
#             WHERE uuid = :employee_id
#         )
#         GROUP BY e.uuid, e.name
#     """
    
#     try:
#         # Get all department employees
#         employees = db.session.execute(text(dept_employees_query), 
#                                      {"employee_id": employee_id}).fetchall()
        
#         # Get work hours
#         work_hours = db.session.execute(text(work_hours_query), {
#             "employee_id": employee_id,
#             "start_date": last_monday,
#             "end_date": last_sunday
#         }).fetchall()
        
#         # Create a mapping of employee_id to work hours
#         hours_map = {row.employee_id: row for row in work_hours}
        
#         # Combine the data
#         result = []
#         for emp in employees:
#             work_data = hours_map.get(emp.uuid, None)
#             result.append({
#                 'employee_id': emp.uuid,
#                 'name': emp.name,
#                 'position': emp.position,
#                 'subdepartment': emp.subdepartment,
#                 'has_reported': work_data is not None and work_data.total_hours is not None,
#                 'total_hours': float(work_data.total_hours) if work_data and work_data.total_hours else 0,
#                 'projects': work_data.projects if work_data else '',
#                 'report_period': {
#                     'start': last_monday.strftime('%Y-%m-%d'),
#                     'end': last_sunday.strftime('%Y-%m-%d')
#                 }
#             })
        
#         return jsonify(result)
        
#     except Exception as e:
#         print(f"Error in list_dept: {str(e)}")
#         return "query execution failed", 500

@app.route('/list_dept', methods=['GET'])
@jwt_required()
def listReport_dept():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    role = user_identity['role']
    
    # Calculate last week's date range
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    
    # First get the user's department and subdepartment
    user_info_query = """
        SELECT department, subdepartment
        FROM employee 
        WHERE uuid = :employee_id
    """
    user_info = db.session.execute(text(user_info_query), 
                                 {"employee_id": employee_id}).first()
    
    if not user_info:
        return "User not found", 404
    
    # Modify query based on user role
    if role == 'level_3':
        # For level 3, only show their subdepartment
        dept_employees_query = """
            SELECT e.uuid, e.name, e.position, e.subdepartment
            FROM employee e 
            WHERE e.department = :department
            AND e.subdepartment = :subdepartment
            ORDER BY e.name
        """
        params = {
            "department": user_info.department,
            "subdepartment": user_info.subdepartment
        }
    else:
        # For level 4, show entire department
        dept_employees_query = """
            SELECT e.uuid, e.name, e.position, e.subdepartment
            FROM employee e 
            WHERE e.department = :department
            ORDER BY e.subdepartment, e.name
        """
        params = {
            "department": user_info.department
        }
    
    # Then get work hours for last week
    work_hours_query = """
        SELECT 
            e.uuid as employee_id,
            e.name as employee_name,
            SUM(wh.hour) as total_hours,
            GROUP_CONCAT(DISTINCT p.name SEPARATOR ', ') as projects,
            MIN(wh.start_date) as earliest_date,
            MAX(wh.end_date) as latest_date
        FROM employee e
        LEFT JOIN work_hour wh ON e.uuid = wh.employee_id 
            AND wh.start_date >= :start_date 
            AND wh.start_date <= :end_date
        LEFT JOIN project p ON wh.project_id = p.uuid
        WHERE e.uuid IN (
            SELECT uuid FROM employee 
            WHERE department = :department
            {subdept_condition}
        )
        GROUP BY e.uuid, e.name
    """
    
    subdept_condition = "AND subdepartment = :subdepartment" if role == 'level_3' else ""
    work_hours_query = work_hours_query.format(subdept_condition=subdept_condition)
    
    try:
        # Get all department/subdepartment employees
        employees = db.session.execute(text(dept_employees_query), params).fetchall()
        
        # Get work hours with added parameters for date range
        work_hours_params = {
            **params,
            "start_date": last_monday,
            "end_date": last_sunday
        }
        work_hours = db.session.execute(text(work_hours_query), work_hours_params).fetchall()
        
        # Create a mapping of employee_id to work hours
        hours_map = {row.employee_id: row for row in work_hours}
        
        # Combine the data
        result = []
        for emp in employees:
            work_data = hours_map.get(emp.uuid, None)
            result.append({
                'employee_id': emp.uuid,
                'name': emp.name,
                'position': emp.position,
                'subdepartment': emp.subdepartment,
                'has_reported': work_data is not None and work_data.total_hours is not None,
                'total_hours': float(work_data.total_hours) if work_data and work_data.total_hours else 0,
                'projects': work_data.projects if work_data else '',
                'report_period': {
                    'start': last_monday.strftime('%Y-%m-%d'),
                    'end': last_sunday.strftime('%Y-%m-%d')
                }
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in list_dept: {str(e)}")
        return "query execution failed", 500

@app.route('/week_summary', methods=['POST'])
@jwt_required()
def week_summary():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    date = request.json.get('date')[:10]
    try:
        result = db.session.execute(text("SELECT project.name AS name, SUM(work_hour.hour) AS hour FROM work_hour JOIN project ON work_hour.project_id = project.uuid WHERE employee_id = :employee_id AND start_date >= :date GROUP BY project.name"), {"employee_id": employee_id, "date": date})
        return jsonify([row._asdict() for row in result])
    except Exception as _:
        print(_)
        return "query execution failed", 500

@app.route('/delete', methods=['POST'])
@jwt_required()
def delete():
    user_identity = json.loads(get_jwt_identity())
    full_query = "DELETE FROM work_hour WHERE uuid = :uuid"
    uuid = request.json.get('uuid')
    print(uuid)
    try:
        db.session.execute(text(full_query), {"uuid": uuid})
        db.session.commit()
        return {"success": 'ok'}
    except Exception as _:
        print(_)
        return "query execution failed", 500

@app.route('/query', methods=['POST'])
@jwt_required()
def execute_query():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    role = user_identity['role']
    # User's query
    user_query = request.json.get('query').replace("`", '').replace("julianday", 'TO_DAYS').replace("JULIANDAY", "TO_DAYS")
    if "SELECT" not in user_query:
        return "query invalid", 400

    user_query = user_query[user_query.index('SELECT'):] if 'WITH' not in user_query else (","+user_query[user_query.index('WITH') + 4: ])

    # Dynamically build the CTE query
    full_query = f"{query_masks[role]} {user_query}"
    print(text(full_query))

    # Execute the query securely
    try: 
        result = db.session.execute(text(full_query), {"employee_id": employee_id})
        return jsonify({'result': [row._asdict() for row in result], 'from_user_security_level': role})
    except Exception as _:
        print(_)
        return "query execution failed", 500

@app.route('/validate', methods=['GET'])
@jwt_required()
def validate():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    return {'id': employee_id}, 200


@app.route('/populate', methods=['POST'])
@jwt_required()
def populate_ID():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    role = user_identity['role']
    # User's query
    project_name = request.json.get('name')

    user_query = "SELECT team.name AS id, project.name as name from team JOIN project ON team.uuid = project.team_id WHERE project.name LIKE :given_name OR team.name LIKE :given_name"

    # Dynamically build the CTE query
    full_query = f"{user_query}"
    print(full_query)
    # Execute the query securely
    try: 
        result = db.session.execute(text(full_query), {"employee_id": employee_id, "given_name": "%"+project_name+"%"})
        return jsonify([row._asdict() for row in result])
    except Exception as _:
        return "query execution failed", 500

@app.route('/delete_kpi', methods=['POST'])
@jwt_required()
def delete_kpi():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    role = user_identity['role']
    if role == 'level_1' or role == 'level_2':
        return 'unauthorized', 401
    
    delquery = """DELETE FROM kpi WHERE kpi_name = :kpi_name AND project_id = :project_id"""
    deltarget = """DELETE FROM target WHERE kpi_name = :kpi_name AND project_id = :project_id"""
    project_uuid = ''
    try:
        project_uuid = str(db.session.execute(text("SELECT project.uuid AS uuid FROM project JOIN team ON project.team_id = team.uuid WHERE team.name = :id"), {"id": request.json.get('project_id')}).first()[0])
        print(project_uuid)
    except Exception as e:
        print(e)
        return "invalid project id", 400
    if not project_uuid:
        return "invalid project id", 400
    try:
        kpi_name = request.json.get('kpi_name')
        db.session.execute(text(delquery), {'kpi_name': kpi_name, 'project_id': project_uuid})
        db.session.execute(text(deltarget), {'kpi_name': kpi_name, 'project_id': project_uuid})
        db.session.commit()
        return {'ok':True}, 200
    except Exception as e:
        print(e)
        return 'Error deleting', 500

@app.route('/report', methods=['POST'])
@jwt_required()
def add_report():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    role = user_identity['role']
    dates = [int(x) for x in request.json.get('date').split("/")]
    print(dates)
    local_timezone = tzlocal.get_localzone()
    local_timezone_key = local_timezone.key
    local_tz = zoneinfo.ZoneInfo(local_timezone_key)
    now = datetime.now()
    end_date = datetime(dates[0], dates[1], dates[2], now.hour, now.minute, now.second, tzinfo=local_tz).date()
    print(datetime(dates[0], dates[1], dates[2], now.hour, now.minute, now.second, tzinfo=local_tz))
    # User's query
    project_rep = request.json.get("Array_input")
    kpi = []
    for i in range(len(project_rep)):
        project_rep[i]['employee_id'] = employee_id
        project_rep[i]['end_date'] = end_date
        project_rep[i]['start_date'] = end_date - timedelta(days=6)
        project_rep[i]['uuid'] = str(uuid.uuid4())
        try:
            project_uuid = str(db.session.execute(text("SELECT project.uuid AS uuid FROM project JOIN team ON project.team_id = team.uuid WHERE team.name = :id"), {"id": project_rep[i]['project_id']}).first()[0])
            print(project_uuid)
            project_rep[i]['project_uuid'] = project_uuid
            print(project_rep[i]['kpi'])
            for y in project_rep[i]['kpi']:
                if (y['kpi_name'] != '#WILDCARD#') or (y['kpi_temp_name'] != ''):
                    kpi.append({
                        'project_id': project_uuid, 
                        'kpi_name': (y['kpi_name'] if y['kpi_name'] != '#WILDCARD#' else y['kpi_temp_name']), 
                        'kpi_value': y['value'] if 'value' in y else 0,
                        'employee_id': project_rep[i]['employee_id'],
                        'date': project_rep[i]['start_date'],
                        'hour': y['hour'] if 'hour' in y else None
                        })
        except Exception as e:
            print(e)
            return {"message":"无效的项目编号："+project_rep[i]['project_id']}, 500
        try:
            project_rep[i]['hour'] = float(project_rep[i]['hour'])
        except Exception as e:
            print(e)
            return {"message":"无效的小时数"+project_rep[i]['hour']+"，来自："+project_rep[i]['project_id']}, 500

    user_query = """INSERT INTO work_hour (uuid, employee_id, project_id, start_date, end_date, is_reversed, is_standardized, task_description, hour, stage)
    VALUES (UUID(), :employee_id, :project_uuid, :start_date, :end_date, :is_reversed, :is_standardized, :description, :hour, :stage)"""
    kpi_query = """INSERT INTO kpi (uuid, employee_id, project_id, date, kpi_name, kpi_value, hour)
    VALUES (UUID(), :employee_id, :project_id, :date, :kpi_name, :kpi_value, :hour)"""
    # Dynamically build the CTE query
    full_query = f"{user_query}"
    # Execute the query securely
    try:
        for x in project_rep:
            find_team = str(db.session.execute(text("SELECT uuid FROM team where name = :team_name"), {'team_name':x['project_id']}).first()[0])
            find_assignment = db.session.execute(text("SELECT uuid FROM team_assignment where team_id = :team_id AND employee_id = :employee_id"), {'team_id': find_team, "employee_id": x['employee_id']}).first()
            print(find_assignment)
            if (not find_assignment):
                db.session.execute(text("INSERT INTO team_assignment (uuid, team_id, employee_id) VALUES (:uuid, :team_id, :employee_id)"), {"uuid":str(uuid.uuid4()), "team_id":find_team, "employee_id":x['employee_id']})
            x.pop('project_id', None)
            db.session.execute(text(full_query), x)
        for x in kpi:
            db.session.execute(text(kpi_query), x)
        db.session.commit()
        return {"ok":True}, 200
    except Exception as _:
        print(_)
        return "submission failed", 500


def get_user_interface(user_id: str) -> CHESSInterface:
    """Get or create a CHESSInterface instance for a user."""
    with interfaces_lock:
        if user_id not in user_interfaces:
            # Use the default config name but create a unique interface
            user_interfaces[user_id] = CHESSInterface(
                config_name="wtl",
                db_mode='dev'
            )
        return user_interfaces[user_id]

@app.route('/create', methods=['POST'])
@jwt_required()
async def create_session():
    """Create a new chat session."""
    try:
        user_identity = json.loads(get_jwt_identity())
        employee_id = user_identity['employee_id']

        # Generate a unique session ID for the frontend
        frontend_session_id = str(uuid.uuid4())
        
        # Get or create user's interface
        interface = get_user_interface(employee_id)

        db_id = "wtl_employee_tracker"
        
        # Create a new CHESS session
        chess_session_id = interface.start_chat_session(db_id)
        
        # Store the mapping
        with sessions_lock:
            active_sessions[frontend_session_id] = chess_session_id
        
        return {
            "session_id": frontend_session_id,
            "db_id": db_id,
            "user_id": employee_id
        }
    except Exception as e:
        logging.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.route('/generate', methods=['POST'])
@jwt_required()
async def query():
    """Handle a query request."""
    try:
        with sessions_lock:
            if request.json.get('session_id') not in active_sessions:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired session ID. Please create a new session."
                )
            chess_session_id = active_sessions[request.json.get('session_id')]

        # Get the user's interface
        interface = get_user_interface(request.json.get("user_id"))

        text = request.json.get('prompt')

        # Split prompt and instructions, and pass instructions as evidence
        parts = text.split("INSTRUCTIONS:")
        prompt = parts[0].strip()
        instructions = parts[1].strip() if len(parts) > 1 else ""
        
        # Extract date from instructions if present
        date_match = re.search(r"today's date is (.*?)\n", instructions)
        date_info = f"\n[DATE]\n{date_match.group(1)}" if date_match else ""
        
        # Format the prompt part with date
        formatted_prompt = f"[EMPLOYEE_ID]\n{request.json.get('user_id')}{date_info}\n\n[QUESTION]\n{prompt}"

        # Process the query using the user's interface with instructions as evidence
        response = interface.chat_query(
            session_id=chess_session_id,
            question=formatted_prompt,
            evidence=instructions
        )

        # Extract just the SQL query from the response
        sql_query = response.get('sql_query', '')
        if not sql_query:
            raise HTTPException(status_code=400, detail="No SQL query was generated")

        return {
            "result": {
                "sql_query": sql_query
            }
        }

        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Optionally, add an endpoint to explicitly end sessions
@app.route("/end_session/{session_id}", methods=['POST'])
@jwt_required()
async def end_session(session_id: str):
    """
    End a chat session explicitly.
    """
    with sessions_lock:
        if session_id in active_sessions:
            # Could add cleanup logic for the CHESS session here if needed
            del active_sessions[session_id]
            return {"message": "Session ended successfully"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.route("/output_import", methods=['POST'])
@jwt_required()
def import_output():
    user_identity = json.loads(get_jwt_identity())
    role = user_identity['role']
    if role != 'level_4' and role != 'level_3':
        return 'unauthorized', 401
    arrInput = request.json.get('arr_input')
    for x in arrInput:
        print(x)
        create_output = 'create_output' in x and x['create_output'] == '1'
        project_uuid = ''
        try:
            project_uuid = str(db.session.execute(text("SELECT project.uuid AS uuid FROM project JOIN team ON project.team_id = team.uuid WHERE team.name = :id"), {"id": x['output_name']}).first()[0])
        except Exception as e:
            if create_output:
                db.session.execute(text("INSERT INTO team (uuid, name) VALUES (UUID(), :id)"), {"id": x['output_name']})
                team_uuid = str(db.session.execute(text("SELECT uuid FROM team WHERE name = :id"), {"id": x['output_name']}).first()[0])
                db.session.execute(text("INSERT INTO project (uuid, name, team_id, is_output) VALUES (UUID(), :id, :team_id, TRUE)"), {"id": x['output_name'], 'team_id': team_uuid})
                project_uuid = str(db.session.execute(text("SELECT project.uuid AS uuid FROM project JOIN team ON project.team_id = team.uuid WHERE team.name = :id"), {"id": x['output_name']}).first()[0])
            else:
                return 'invalid output name '+x['output_name'], 400
        target_value = x['target_value']
        now = datetime.now()
        start_date = now.date()
        end_date = None
        if 'deadline' in x and x['deadline']:
            try:
                print(x['deadline'].split('-'))
                dates = [int(y) for y in (x['deadline'].split('-'))]
                local_timezone = tzlocal.get_localzone()
                local_timezone_key = local_timezone.key
                local_tz = zoneinfo.ZoneInfo(local_timezone_key)
                end_date = datetime(dates[0], dates[1], dates[2], now.hour, now.minute, now.second, tzinfo=local_tz)
                end_date = end_date.date()
            except Exception as e:
                print(e)
                return 'invalid date '+x['deadline'], 400
        employee_name = x['employee'] if 'employee' in x else None
        employee_id = employee_name
        if employee_name:
            try:
                employee_id = str(db.session.execute(text("SELECT uuid from employee where name = :employee"), {'employee': employee_name}).first()[0])
                try:
                    team_uuid = str(db.session.execute(text("SELECT uuid FROM team WHERE name = :id"), {"id": x['output_name']}).first()[0])
                    db.session.execute(text("INSERT INTO team_assignment (uuid, employee_id, team_id) VALUES (UUID(), :employee_id, :team_id)"), {"employee_id": employee_id, "team_id": team_uuid})
                except Exception as e:
                    print("employee "+employee_name+" already exists, skipping team_assignment")
            except Exception as e:
                print(e)
                return 'Invalid employee name '+employee_id, 400
        target_value = x['target_value']
        kpi_name = x['kpi_name']
        query = """INSERT INTO target (uuid, employee_id, project_id, target_value, kpi_name, start_date, end_date)
        VALUES (UUID(),  :employee_id, :project_id, :target_value, :kpi_name, :start_date, :end_date)"""
        db.session.execute(text(query), {'employee_id': employee_id, 'project_id': project_uuid, 'kpi_name': kpi_name, 'start_date': start_date, 'end_date': end_date, 'target_value': target_value})
    db.session.commit()
    return {'ok': True}, 200


@app.route('/check_missing_reports', methods=['POST'])
@jwt_required()
def check_missing_reports():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file:
        try:
            # Skip the title row and use the second row as headers
            df = pd.read_excel(file, header=1)
            print("Reading Excel file...")
            print("Excel columns:", df.columns.tolist())
            
            # The actual column name in your Excel is '姓名'
            name_column = '姓名'
            if name_column not in df.columns:
                print(f"Required column '{name_column}' not found. Available columns: {df.columns.tolist()}")
                return jsonify({'message': f'Excel file must contain a column named "{name_column}"'}), 400
            
            # Clean the names - remove any leading/trailing whitespace
            df[name_column] = df[name_column].astype(str).str.strip()
            excel_names = set(df[name_column].dropna().tolist())
            
            print("Names from Excel:", list(excel_names)[:5])
            print("Total unique names:", len(excel_names))

            # Calculate date range for last week
            today = date.today()
            last_monday = today - timedelta(days=today.weekday() + 7)
            last_sunday = last_monday + timedelta(days=6)
            print(f"Date range: {last_monday} to {last_sunday}")

            # First query: Get all names that reported last week
            reporters_query = text("""
                SELECT e.name, SUM(wh.hour) AS hour
                FROM employee e
                JOIN work_hour wh ON e.uuid = wh.employee_id 
                WHERE wh.start_date >= :start_date 
                AND wh.start_date <= :end_date
                GROUP BY e.name
            """)

            # Second query: Get employee details for all names in Excel
            employees_query = text("""
                SELECT e.uuid as employee_id, e.name as employee_name, 
                       e.alias as employee_alias, e.department as department,
                       e.subdepartment as subdepartment, e.position as position
                FROM employee e
                WHERE e.name IN :employee_names
            """)
            
            try:
                # Execute first query to get who reported
                reporters_result = db.session.execute(reporters_query, {
                    "start_date": last_monday, 
                    "end_date": last_sunday
                })
                reporters = set()
                duplicates = set()
                for x in reporters_result:
                    if x.hour > 60:
                        duplicates.add(x.name)
                    else:
                        reporters.add(x.name)
                
                print(f"Found {len(reporters)} people who reported last week")
                print(f"Found {len(duplicates)} people who reported more than 60 hours last week")

                # Execute second query to get employee details
                names_tuple = tuple(excel_names)  # Convert set to tuple for SQL IN clause
                excel_employees_result = db.session.execute(employees_query, {
                    "employee_names": names_tuple
                })
                excel_employees = list(excel_employees_result)
                
                # Check for names in Excel that aren't in database
                db_names = {row.employee_name for row in excel_employees}
                not_in_db = excel_names - db_names
                if not_in_db:
                    print(f"Warning: These names from Excel are not in database: {not_in_db}")
                
                # Create list of missing reporters
                missing_reporters = [{
                    'id': row.employee_id,
                    'name': row.employee_name,
                    'alias': row.employee_alias,
                    'department': row.department,
                    'subdepartment': row.subdepartment,
                    'position': row.position,
                    'error': '疑似重复提交（超过60小时）' if row.employee_name in duplicates else '未提交'
                } for row in excel_employees if row.employee_name not in reporters or row.employee_name in duplicates]

                print(f"Found {len(missing_reporters)} missing reporters")

                response_data = {
                    'missing_reporters': missing_reporters,
                    'period': {
                        'start_date': last_monday.strftime('%Y-%m-%d'),
                        'end_date': last_sunday.strftime('%Y-%m-%d')
                    }
                }

                # Add warnings about names not in DB if any exist
                if not_in_db:
                    response_data['warnings'] = {
                        'names_not_in_database': list(not_in_db)
                    }

                return jsonify(response_data), 200

            except Exception as db_error:
                print(f"Database error: {str(db_error)}")
                return jsonify({'message': f'Database error: {str(db_error)}'}), 500

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            return jsonify({
                'message': f'Error processing file: {str(e)}',
                'details': error_details
            }), 500

    return jsonify({'message': 'Unknown error occurred'}), 500


# @app.route('/edit_dept_entry', methods=['POST'])
# @jwt_required()
# def edit_dept_entry():
#     user_identity = json.loads(get_jwt_identity())
#     employee_id = user_identity['employee_id']
#     role = user_identity['role']
    
#     if role == 'level_1':
#         return jsonify({'message': 'Unauthorized'}), 401
    
#     entry_id = request.json.get('entry_id')
#     if not entry_id:
#         return jsonify({'message': 'Missing entry ID'}), 400
        
#     # Get department of editing user and verify authorization
#     try:
#         # First get editor's department
#         dept_query = "SELECT department FROM employee WHERE uuid = :employee_id"
#         editor_dept = db.session.execute(text(dept_query), 
#                                        {"employee_id": employee_id}).first()
        
#         if not editor_dept:
#             return jsonify({'message': 'Editor not found'}), 404
            
#         # Then verify target entry is in same department
#         verify_query = """
#             SELECT work_hour.*, employee.department 
#             FROM work_hour 
#             JOIN employee ON employee.uuid = work_hour.employee_id 
#             WHERE work_hour.uuid = :entry_id
#         """
#         entry = db.session.execute(text(verify_query), 
#                                       {"entry_id": entry_id}).first()
        
#         if not entry:
#             return jsonify({'message': 'Entry not found'}), 404
            
#         if entry.department != editor_dept[0]:
#             return jsonify({'message': 'Unauthorized - different department'}), 401

#         # Store old values for logging
#         old_values = {
#             'hour': entry.hour,
#             'task_description': entry.task_description,
#             'is_reversed': entry.is_reversed,
#             'is_standardized': entry.is_standardized
#         }

#         # Get new values from request, using old values as defaults
#         new_values = {
#             'hour': request.json.get('hour', old_values['hour']),
#             'task_description': request.json.get('task_description', old_values['task_description']),
#             'is_reversed': request.json.get('is_reversed', old_values['is_reversed']),
#             'is_standardized': request.json.get('is_standardized', old_values['is_standardized'])
#         }

#         # Perform update
#         update_query = """
#             UPDATE work_hour 
#             SET hour = :new_hours,
#                 task_description = :new_desc,
#                 is_reversed = :new_reversed,
#                 is_standardized = :new_standardized
#             WHERE uuid = :entry_id
#         """
#         db.session.execute(text(update_query), {
#             "entry_id": entry_id,
#             "new_hours": new_values['hour'],
#             "new_desc": new_values['task_description'],
#             "new_reversed": new_values['is_reversed'],
#             "new_standardized": new_values['is_standardized']
#         })
        
#         # Log the edit
#         log_query = """
#             INSERT INTO edit_log (uuid, entry_id, editor_id, edit_time, old_value, new_value)
#             VALUES (UUID(), :entry_id, :editor_id, NOW(), :old_value, :new_value)
#         """
#         db.session.execute(text(log_query), {
#             "entry_id": entry_id,
#             "editor_id": employee_id,
#             "old_value": json.dumps(old_values),
#             "new_value": json.dumps(new_values)
#         })
        
#         db.session.commit()
#         return jsonify({'message': 'Update successful'}), 200
        
#     except Exception as e:
#         db.session.rollback()
#         print(e)
#         return jsonify({'message': 'Update failed', 'error': str(e)}), 500

@app.route('/edit_dept_entry', methods=['POST'])
@jwt_required()
def edit_dept_entry():
    user_identity = json.loads(get_jwt_identity())
    employee_id = user_identity['employee_id']
    role = user_identity['role']
    
    entry_id = request.json.get('entry_id')
    if not entry_id:
        return jsonify({'message': 'Missing entry ID'}), 400
        
    try:
        # First verify the entry exists and get its details
        verify_query = """
            SELECT work_hour.*, employee.department, work_hour.employee_id AS owner_id
            FROM work_hour 
            JOIN employee ON employee.uuid = work_hour.employee_id 
            WHERE work_hour.uuid = :entry_id
        """
        entry = db.session.execute(text(verify_query), 
                                      {"entry_id": entry_id}).first()
        
        if not entry:
            return jsonify({'message': 'Entry not found'}), 404

        # Check authorization:
        # 1. Level 1 users can only edit their own entries
        # 2. Level 2+ users can edit entries in their department
        if role == 'level_1':
            if entry.owner_id != employee_id:
                return jsonify({'message': 'Unauthorized - can only edit own entries'}), 401
        else:
            # For level 2+ users, check department access
            dept_query = "SELECT department FROM employee WHERE uuid = :employee_id"
            editor_dept = db.session.execute(text(dept_query), 
                                           {"employee_id": employee_id}).first()
            
            if not editor_dept:
                return jsonify({'message': 'Editor not found'}), 404
                
            if entry.department != editor_dept[0]:
                return jsonify({'message': 'Unauthorized - different department'}), 401

        # Store old values for logging, converting Decimal to float
        old_values = {
            'hour': decimal_to_float(entry.hour),
            'task_description': entry.task_description,
            'is_reversed': entry.is_reversed,
            'is_standardized': entry.is_standardized
        }

        # Get new values from request, using old values as defaults
        new_values = {
            'hour': decimal_to_float(request.json.get('hour', old_values['hour'])),
            'task_description': request.json.get('task_description', old_values['task_description']),
            'is_reversed': request.json.get('is_reversed', old_values['is_reversed']),
            'is_standardized': request.json.get('is_standardized', old_values['is_standardized'])
        }

        # Perform update
        update_query = """
            UPDATE work_hour 
            SET hour = :new_hours,
                task_description = :new_desc,
                is_reversed = :new_reversed,
                is_standardized = :new_standardized
            WHERE uuid = :entry_id
        """
        db.session.execute(text(update_query), {
            "entry_id": entry_id,
            "new_hours": new_values['hour'],
            "new_desc": new_values['task_description'],
            "new_reversed": new_values['is_reversed'],
            "new_standardized": new_values['is_standardized']
        })
        
        # Log the edit
        log_query = """
            INSERT INTO edit_log (uuid, entry_id, editor_id, edit_time, old_value, new_value)
            VALUES (UUID(), :entry_id, :editor_id, NOW(), :old_value, :new_value)
        """
        db.session.execute(text(log_query), {
            "entry_id": entry_id,
            "editor_id": employee_id,
            "old_value": json.dumps(old_values),
            "new_value": json.dumps(new_values)
        })
        
        db.session.commit()
        return jsonify({'message': 'Update successful'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in edit_dept_entry: {str(e)}")
        return jsonify({'message': 'Update failed', 'error': str(e)}), 500


if __name__ == '__main__':
    print("Tables in SQLAlchemy:", db.metadata.tables.keys())
    app.run(host='0.0.0.0', port=8888, debug=True)
