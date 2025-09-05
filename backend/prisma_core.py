# prisma_core.py
# Core functionality for PRISMA framework implementation

import streamlit as st
import pandas as pd
import numpy as np
import json
import sqlite3
import os
import traceback
import psutil  # For system resource monitoring
import time
from datetime import datetime
from pathlib import Path

# Database setup
DATA_DIR = 'data'
DB_NAME = 'prisma_reviews.db'

def get_db_path():
    """Get the absolute path to the database file"""
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    # Return absolute path to database
    return os.path.join(Path().absolute(), DATA_DIR, DB_NAME)

# Database functions for PRISMA reviews
def init_prisma_db():
    """Initialize the PRISMA database"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        # Create reviews table
        c.execute('''
        CREATE TABLE IF NOT EXISTS prisma_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            question TEXT NOT NULL,
            created_date TEXT NOT NULL,
            updated_date TEXT NOT NULL,
            status TEXT NOT NULL,
            config TEXT,
            search_strategy TEXT,
            inclusion_criteria TEXT,
            exclusion_criteria TEXT
        )
        ''')
        
        # Create table for studies in reviews
        c.execute('''
        CREATE TABLE IF NOT EXISTS prisma_studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            pmid TEXT,
            title TEXT NOT NULL,
            authors TEXT,
            journal TEXT,
            pub_date TEXT,
            abstract TEXT,
            status TEXT NOT NULL,
            screening_notes TEXT,
            eligibility_notes TEXT,
            data_extracted TEXT,
            FOREIGN KEY (review_id) REFERENCES prisma_reviews(id)
        )
        ''')
        
        conn.commit()
        conn.close()
        st.success("PRISMA database initialized successfully")
        return True
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        st.error(traceback.format_exc())
        return False

def optimize_db_for_large_import():
    """Optimize database settings for large imports"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA cache_size=10000')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error optimizing database: {str(e)}")
        return False

def monitor_system_resources():
    """Monitor system resources during import"""
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_available_gb = memory.available / (1024**3)
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'memory_available_gb': memory_available_gb,
        'is_healthy': cpu_percent < 90 and memory_percent < 90
    }

def add_studies_to_review_batch(review_id, studies, batch_size=1000, chunk_size=50000):
    """
    Add articles/studies to a PRISMA review in batches with chunking support
    
    Parameters:
    review_id: Review ID
    studies: List of studies to add
    batch_size: Number of studies to process in each database batch
    chunk_size: Maximum number of studies to process in one go
    
    Returns:
    Total number of studies added
    """
    if not studies:
        st.warning("No studies provided to add")
        return 0
    
    total_studies = len(studies)
    
    # If we have more studies than chunk_size, process in chunks
    if total_studies > chunk_size:
        st.info(f"Large dataset detected ({total_studies} studies). Processing in chunks of {chunk_size}...")
        
        total_added = 0
        for chunk_start in range(0, total_studies, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_studies)
            chunk = studies[chunk_start:chunk_end]
            
            st.info(f"Processing chunk {chunk_start//chunk_size + 1}: Studies {chunk_start + 1} to {chunk_end}")
            added = _add_studies_batch_internal(review_id, chunk, batch_size)
            total_added += added
            
            # Add a small delay between chunks to prevent overload
            time.sleep(1)
            
        return total_added
    else:
        return _add_studies_batch_internal(review_id, studies, batch_size)

def _add_studies_batch_internal(review_id, studies, batch_size=1000):
    """Internal function to add studies in batches with progress tracking"""
    total_added = 0
    total_studies = len(studies)
    
    # Create progress tracking elements
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        resource_text = st.empty()
    
    try:
        # Optimize database for large imports
        optimize_db_for_large_import()
        
        conn = sqlite3.connect(get_db_path())
        
        # Get existing PMIDs to avoid duplicates
        existing_pmids = set()
        c = conn.cursor()
        c.execute('SELECT pmid FROM prisma_studies WHERE review_id = ?', (review_id,))
        existing_pmids = {row[0] for row in c.fetchall() if row[0]}
        
        # Process in batches
        start_time = time.time()
        for i in range(0, total_studies, batch_size):
            batch = studies[i:i + batch_size]
            batch_added = 0
            
            # Check system resources
            resources = monitor_system_resources()
            resource_text.text(f"CPU: {resources['cpu_percent']}% | Memory: {resources['memory_percent']}% | Available: {resources['memory_available_gb']:.1f}GB")
            
            if not resources['is_healthy']:
                st.warning("System resources are running low. Pausing for 5 seconds...")
                time.sleep(5)
            
            # Begin transaction for this batch
            conn.execute('BEGIN TRANSACTION')
            
            try:
                for study in batch:
                    # Skip if already exists
                    if study.get('pmid') and study['pmid'] in existing_pmids:
                        continue
                    
                    c.execute('''
                    INSERT INTO prisma_studies
                    (review_id, pmid, title, authors, journal, pub_date, abstract, status, screening_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        review_id,
                        study.get('pmid', ''),
                        study.get('title', 'No title'),
                        study.get('authors', ''),
                        study.get('journal', ''),
                        study.get('pub_date', ''),
                        study.get('abstract', ''),
                        'identified',
                        ''
                    ))
                    batch_added += 1
                
                conn.commit()
                total_added += batch_added
                
                # Update progress
                progress = min((i + batch_size) / total_studies, 1.0)
                progress_bar.progress(progress)
                
                # Calculate time estimates
                elapsed_time = time.time() - start_time
                rate = total_added / elapsed_time if elapsed_time > 0 else 0
                remaining = total_studies - (i + batch_size)
                eta = remaining / rate if rate > 0 else 0
                
                status_text.text(f"Imported {total_added} of {total_studies} studies... (Rate: {rate:.1f}/sec, ETA: {eta:.1f}s)")
                
            except Exception as e:
                conn.rollback()
                st.error(f"Error in batch {i//batch_size + 1}: {str(e)}")
                continue
        
        # Final progress update
        progress_bar.progress(1.0)
        status_text.text(f"Import completed! Imported {total_added} of {total_studies} studies in {elapsed_time:.1f} seconds.")
        
    except Exception as e:
        st.error(f"Error during import: {str(e)}")
        st.error(traceback.format_exc())
    finally:
        if 'conn' in locals() and conn:
            conn.close()
        
        # Clean up progress indicators after a delay
        time.sleep(2)
        progress_container.empty()
    
    return total_added

def create_new_review(username, title, question, inclusion_criteria, exclusion_criteria):
    """Create a new PRISMA review"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        current_date = datetime.now().isoformat()
        
        # Initial configuration with default settings
        config = json.dumps({
            "duplicate_detection": "title_abstract",
            "min_reviewers": 1,
            "require_full_text": True
        })
        
        c.execute('''
        INSERT INTO prisma_reviews 
        (username, title, question, created_date, updated_date, status, config, 
        inclusion_criteria, exclusion_criteria)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            username, 
            title, 
            question, 
            current_date, 
            current_date, 
            "identification", 
            config,
            json.dumps(inclusion_criteria),
            json.dumps(exclusion_criteria)
        ))
        
        review_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return review_id
    except Exception as e:
        st.error(f"Error creating review: {str(e)}")
        st.error(traceback.format_exc())
        return None

def get_user_reviews(username):
    """Get all PRISMA reviews for a user"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        c.execute('''
        SELECT id, title, question, status, created_date, updated_date
        FROM prisma_reviews
        WHERE username = ?
        ORDER BY updated_date DESC
        ''', (username,))
        
        reviews = []
        for row in c.fetchall():
            reviews.append({
                "id": row[0],
                "title": row[1],
                "question": row[2],
                "status": row[3],
                "created_date": row[4],
                "updated_date": row[5]
            })
        
        conn.close()
        return reviews
    except Exception as e:
        st.error(f"Error getting user reviews: {str(e)}")
        return []

def get_review_details(review_id):
    """Get details of a specific review"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        c.execute('''
        SELECT id, username, title, question, status, created_date, updated_date,
        config, search_strategy, inclusion_criteria, exclusion_criteria
        FROM prisma_reviews
        WHERE id = ?
        ''', (review_id,))
        
        row = c.fetchone()
        if not row:
            conn.close()
            return None
        
        review = {
            "id": row[0],
            "username": row[1],
            "title": row[2],
            "question": row[3],
            "status": row[4],
            "created_date": row[5],
            "updated_date": row[6],
            "config": json.loads(row[7]) if row[7] else {},
            "search_strategy": row[8],
            "inclusion_criteria": json.loads(row[9]) if row[9] else [],
            "exclusion_criteria": json.loads(row[10]) if row[10] else []
        }
        
        conn.close()
        return review
    except Exception as e:
        st.error(f"Error getting review details: {str(e)}")
        return None

def update_review_status(review_id, status):
    """Update the status of a PRISMA review"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        current_date = datetime.now().isoformat()
        
        c.execute('''
        UPDATE prisma_reviews
        SET status = ?, updated_date = ?
        WHERE id = ?
        ''', (status, current_date, review_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating review status: {str(e)}")
        return False

def update_review_search_strategy(review_id, search_strategy):
    """Update the search strategy of a PRISMA review"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        current_date = datetime.now().isoformat()
        
        c.execute('''
        UPDATE prisma_reviews
        SET search_strategy = ?, updated_date = ?
        WHERE id = ?
        ''', (search_strategy, current_date, review_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating search strategy: {str(e)}")
        return False

def add_studies_to_review(review_id, studies):
    """Legacy function - redirects to batch import"""
    return add_studies_to_review_batch(review_id, studies)

def get_review_studies(review_id, status=None):
    """Get all studies for a specific review, optionally filtered by status"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        if status:
            c.execute('''
            SELECT id, pmid, title, authors, journal, pub_date, abstract, status, 
            screening_notes, eligibility_notes
            FROM prisma_studies
            WHERE review_id = ? AND status = ?
            ORDER BY id ASC
            ''', (review_id, status))
        else:
            c.execute('''
            SELECT id, pmid, title, authors, journal, pub_date, abstract, status,
            screening_notes, eligibility_notes
            FROM prisma_studies
            WHERE review_id = ?
            ORDER BY id ASC
            ''', (review_id,))
        
        studies = []
        for row in c.fetchall():
            studies.append({
                "id": row[0],
                "pmid": row[1],
                "title": row[2],
                "authors": row[3],
                "journal": row[4],
                "pub_date": row[5],
                "abstract": row[6],
                "status": row[7],
                "screening_notes": row[8],
                "eligibility_notes": row[9]
            })
        
        conn.close()
        return studies
    except Exception as e:
        st.error(f"Error retrieving review studies: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()
        return []

def update_study_status(study_id, status, notes=""):
    """Update the status of a study in the PRISMA process"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        if status == "screened_included" or status == "screened_excluded":
            c.execute('''
            UPDATE prisma_studies
            SET status = ?, screening_notes = ?
            WHERE id = ?
            ''', (status, notes, study_id))
        elif status == "eligible" or status == "not_eligible":
            c.execute('''
            UPDATE prisma_studies
            SET status = ?, eligibility_notes = ?
            WHERE id = ?
            ''', (status, notes, study_id))
        else:
            c.execute('''
            UPDATE prisma_studies
            SET status = ?
            WHERE id = ?
            ''', (status, study_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating study status: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()
        return False

def get_prisma_stats(review_id):
    """Get statistics for PRISMA flow diagram"""
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        # Get counts for each stage
        c.execute("SELECT COUNT(*) FROM prisma_studies WHERE review_id = ?", (review_id,))
        total_records = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM prisma_studies WHERE review_id = ? AND status = 'identified'", (review_id,))
        identified = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM prisma_studies WHERE review_id = ? AND status = 'screened_included'", (review_id,))
        screened_included = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM prisma_studies WHERE review_id = ? AND status = 'screened_excluded'", (review_id,))
        screened_excluded = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM prisma_studies WHERE review_id = ? AND status = 'eligible'", (review_id,))
        eligible = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM prisma_studies WHERE review_id = ? AND status = 'not_eligible'", (review_id,))
        not_eligible = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM prisma_studies WHERE review_id = ? AND status = 'included'", (review_id,))
        included = c.fetchone()[0]
        
        conn.close()
        
        # Prepare statistics for PRISMA flow diagram
        stats = {
            "total_records": total_records,
            "identified": identified,
            "screened": {
                "total": screened_included + screened_excluded + identified,
                "included": screened_included,
                "excluded": screened_excluded,
                "pending": identified
            },
            "eligibility": {
                "total": eligible + not_eligible + screened_included,
                "included": eligible,
                "excluded": not_eligible,
                "pending": screened_included - (eligible + not_eligible)
            },
            "included": {
                "total": included,
                "pending": eligible - included
            }
        }
        
        return stats
    except Exception as e:
        st.error(f"Error getting PRISMA stats: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()
        return {
            "total_records": 0,
            "identified": 0,
            "screened": {"total": 0, "included": 0, "excluded": 0, "pending": 0},
            "eligibility": {"total": 0, "included": 0, "excluded": 0, "pending": 0},
            "included": {"total": 0, "pending": 0}
        }

def deduplicate_studies(review_id, method="title_abstract"):
    """
    Deduplicate studies in a review
    
    Parameters:
    review_id: ID of the review
    method: Method to use for deduplication (title_abstract, pmid, etc.)
    
    Returns:
    Number of duplicates found
    """
    try:
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        # Get all studies
        c.execute('''
        SELECT id, pmid, title, abstract
        FROM prisma_studies
        WHERE review_id = ? AND status = 'identified'
        ''', (review_id,))
        
        studies = []
        for row in c.fetchall():
            studies.append({
                "id": row[0],
                "pmid": row[1],
                "title": row[2].lower() if row[2] else "",
                "abstract": row[3].lower() if row[3] else ""
            })
        
        # Find duplicates
        duplicates = []
        processed = []
        
        if method == "pmid":
            # Use PMID for deduplication
            pmid_dict = {}
            for study in studies:
                if study["pmid"] and study["pmid"] in pmid_dict:
                    duplicates.append(study["id"])
                elif study["pmid"]:
                    pmid_dict[study["pmid"]] = study["id"]
        
        elif method == "title_abstract":
            # Use title and first 200 chars of abstract for deduplication
            for study in studies:
                key = f"{study['title'][:100]}_{study['abstract'][:100]}"
                if key in processed:
                    duplicates.append(study["id"])
                else:
                    processed.append(key)
        
        # Mark duplicates as excluded
        for study_id in duplicates:
            c.execute('''
            UPDATE prisma_studies
            SET status = 'screened_excluded', screening_notes = 'Automatically marked as duplicate'
            WHERE id = ?
            ''', (study_id,))
        
        conn.commit()
        conn.close()
        
        return len(duplicates)
    except Exception as e:
        st.error(f"Error deduplicating studies: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()
        return 0

def export_prisma_data(review_id, format="csv"):
    """
    Export PRISMA review data
    
    Parameters:
    review_id: ID of the review
    format: Export format (csv, json)
    
    Returns:
    Data in the requested format
    """
    try:
        # Get review details
        review = get_review_details(review_id)
        if not review:
            return None
        
        # Get all studies
        studies = get_review_studies(review_id)
        
        # Get statistics
        stats = get_prisma_stats(review_id)
        
        export_data = {
            "review": review,
            "studies": studies,
            "statistics": stats
        }
        
        if format == "json":
            return json.dumps(export_data, indent=4)
        elif format == "csv":
            # Convert studies to dataframe
            df = pd.DataFrame(studies)
            return df.to_csv(index=False)
        
        return None
    except Exception as e:
        st.error(f"Error exporting PRISMA data: {str(e)}")
        return None

def test_db_connection():
    """Test function to verify database connection works"""
    try:
        conn = sqlite3.connect(get_db_path())
        if conn:
            st.success("Database connection successful!")
            conn.close()
            return True
        else:
            st.error("Database connection failed")
            return False
    except Exception as e:
        st.error(f"Error in test connection: {str(e)}")
        return False