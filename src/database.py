"""
SQLite database module for persistent storage of extraction projects.
Handles all database operations for the Architectural PDF Extractor.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import streamlit as st


class ExtractionDatabase:
    """SQLite database manager for extraction projects."""

    def __init__(self, db_path: str = "extraction_projects.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database schema if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_pages INTEGER,
                    analysis_json TEXT NOT NULL,
                    user_feedback TEXT,
                    refined_analysis_json TEXT,
                    UNIQUE(project_name)
                )
            """)

            # Create extraction history (for tracking refinements)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extraction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    analysis_json TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    refinement_reason TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Create field refinements (for tracking individual field challenges)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS field_refinements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    field_code TEXT NOT NULL,
                    original_value TEXT,
                    refined_value TEXT,
                    user_feedback TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database initialization failed: {e}")
            self.db_path = None

    def save_project(self, project_name: str, filename: str, analysis_json: dict, total_pages: int) -> int:
        """
        Save a new extraction project to the database.

        Args:
            project_name: Name of the project
            filename: Original PDF filename
            analysis_json: Full analysis result JSON
            total_pages: Total number of pages in the PDF

        Returns:
            Project ID
        """
        if self.db_path is None:
            return None
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO projects (project_name, filename, total_pages, analysis_json)
                VALUES (?, ?, ?, ?)
            """, (project_name, filename, total_pages, json.dumps(analysis_json)))

            project_id = cursor.lastrowid

            # Record in history (version 1)
            cursor.execute("""
                INSERT INTO extraction_history (project_id, version, analysis_json, refinement_reason)
                VALUES (?, 1, ?, 'Initial extraction')
            """, (project_id, json.dumps(analysis_json)))

            conn.commit()
            return project_id

        except sqlite3.IntegrityError:
            # Project already exists, update it
            cursor.execute("""
                UPDATE projects
                SET analysis_json = ?, updated_at = CURRENT_TIMESTAMP, total_pages = ?
                WHERE project_name = ?
            """, (json.dumps(analysis_json), total_pages, project_name))

            cursor.execute("SELECT id FROM projects WHERE project_name = ?", (project_name,))
            project_id = cursor.fetchone()[0]
            conn.commit()
            return project_id
        finally:
            conn.close()

    def get_all_projects(self) -> List[Dict]:
        """
        Retrieve all projects from the database.

        Returns:
            List of project dictionaries with id, project_name, created_at, updated_at, total_pages
        """
        if self.db_path is None:
            return []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_name, filename, created_at, updated_at, total_pages
            FROM projects
            ORDER BY updated_at DESC
        """)

        columns = [description[0] for description in cursor.description]
        projects = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return projects

    def get_project(self, project_id: int) -> Optional[Dict]:
        """
        Retrieve a specific project.

        Args:
            project_id: ID of the project

        Returns:
            Project dictionary with full analysis JSON
        """
        if self.db_path is None:
            return None
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_name, filename, created_at, updated_at, total_pages, analysis_json, user_feedback, refined_analysis_json
            FROM projects
            WHERE id = ?
        """, (project_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            columns = [description[0] for description in cursor.description]
            project = dict(zip(columns, row))
            # Parse JSON fields
            project["analysis_json"] = json.loads(project["analysis_json"])
            if project["refined_analysis_json"]:
                project["refined_analysis_json"] = json.loads(project["refined_analysis_json"])
            return project
        return None

    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project and all associated data.

        Args:
            project_id: ID of the project to delete

        Returns:
            True if successful, False otherwise
        """
        if self.db_path is None:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Delete associated refinements
            cursor.execute("DELETE FROM field_refinements WHERE project_id = ?", (project_id,))

            # Delete history
            cursor.execute("DELETE FROM extraction_history WHERE project_id = ?", (project_id,))

            # Delete project
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting project: {str(e)}")
            return False
        finally:
            conn.close()

    def add_field_refinement(self, project_id: int, field_code: str, original_value: str, 
                           refined_value: str, user_feedback: str) -> bool:
        """
        Record a field refinement/challenge.

        Args:
            project_id: ID of the project
            field_code: Field code that was refined
            original_value: Original extracted value
            refined_value: New refined value
            user_feedback: User's feedback/explanation

        Returns:
            True if successful
        """
        if self.db_path is None:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO field_refinements (project_id, field_code, original_value, refined_value, user_feedback)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, field_code, original_value, refined_value, user_feedback))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding refinement: {str(e)}")
            return False
        finally:
            conn.close()

    def update_refined_analysis(self, project_id: int, refined_analysis_json: dict, user_feedback: str) -> bool:
        """
        Update a project with refined analysis results.

        Args:
            project_id: ID of the project
            refined_analysis_json: Refined analysis result
            user_feedback: User's feedback that triggered the refinement

        Returns:
            True if successful
        """
        if self.db_path is None:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE projects
                SET refined_analysis_json = ?, user_feedback = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(refined_analysis_json), user_feedback, project_id))

            # Also record in history
            cursor.execute("""
                SELECT MAX(version) FROM extraction_history WHERE project_id = ?
            """, (project_id,))
            max_version = cursor.fetchone()[0] or 0

            cursor.execute("""
                INSERT INTO extraction_history (project_id, version, analysis_json, refinement_reason)
                VALUES (?, ?, ?, ?)
            """, (project_id, max_version + 1, json.dumps(refined_analysis_json), 
                  f"User refinement: {user_feedback}"))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating refined analysis: {str(e)}")
            return False
        finally:
            conn.close()

    def get_field_refinements(self, project_id: int) -> List[Dict]:
        """
        Get all refinements for a project.

        Args:
            project_id: ID of the project

        Returns:
            List of refinement records
        """
        if self.db_path is None:
            return []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT field_code, original_value, refined_value, user_feedback, timestamp
            FROM field_refinements
            WHERE project_id = ?
            ORDER BY timestamp DESC
        """, (project_id,))

        columns = [description[0] for description in cursor.description]
        refinements = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return refinements

    def get_project_by_name(self, project_name: str) -> Optional[Dict]:
        """
        Retrieve a project by name.

        Args:
            project_name: Name of the project

        Returns:
            Project dictionary or None
        """
        if self.db_path is None:
            return None
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_name, filename, created_at, updated_at, total_pages, analysis_json
            FROM projects
            WHERE project_name = ?
        """, (project_name,))

        row = cursor.fetchone()
        conn.close()

        if row:
            columns = [description[0] for description in cursor.description]
            project = dict(zip(columns, row))
            project["analysis_json"] = json.loads(project["analysis_json"])
            return project
        return None


def get_db() -> ExtractionDatabase:
    """Get or create database instance (Streamlit singleton pattern)."""
    if "db" not in st.session_state:
        st.session_state.db = ExtractionDatabase()
    return st.session_state.db
