import pandas as pd
import json
import csv
from typing import List, Dict, Any, Optional, Tuple
from io import StringIO
from app.models.import_models import (
    JournalistImportRow, ImportPreview, ImportResult, 
    ImportJob, ImportFileType, ImportStatus
)
from app.models.journalist import Journalist, JournalistCategory
from app.models.user import User
from fastapi import HTTPException, status, UploadFile
import uuid
from datetime import datetime
import re

class ImportService:
    
    def __init__(self):
        self.field_mapping_suggestions = {
            # Common variations for name
            'name': ['name', 'full_name', 'journalist_name', 'contact_name', 'reporter_name', 'full name', 'journalist name'],
            # Common variations for email
            'email': ['email', 'email_address', 'contact_email', 'e_mail', 'mail', 'email address', 'e-mail'],
            # Common variations for publication
            'publication': ['publication', 'media', 'outlet', 'newspaper', 'magazine', 'media_outlet', 'news_outlet', 'company'],
            # Common variations for category/beat
            'category': ['category', 'beat', 'sector', 'industry', 'focus', 'specialty', 'vertical', 'coverage_area'],
            # Common variations for location
            'country': ['country', 'location', 'region', 'nation', 'geography', 'territory'],
            # Contact information
            'phone': ['phone', 'telephone', 'mobile', 'contact_number', 'phone_number', 'tel'],
            'website': ['website', 'url', 'web', 'site', 'homepage'],
            'twitter': ['twitter', 'twitter_handle', '@twitter', 'twitter_username'],
            'linkedin': ['linkedin', 'linkedin_url', 'linkedin_profile']
        }
    
    async def preview_import_file(
        self, 
        file: UploadFile, 
        current_user: User
    ) -> ImportPreview:
        """Preview import file and suggest field mappings"""
        
        try:
            # Read file content
            content = await file.read()
            file_type = self._detect_file_type(file.filename)
            
            # Parse file content
            data_rows, column_names = await self._parse_file_content(content, file_type)
            
            # Suggest field mappings
            suggested_mapping = self._suggest_field_mapping(column_names)
            
            # Create preview data with suggested mapping
            preview_data = []
            valid_count = 0
            invalid_count = 0
            
            # Process first 10 rows for preview
            for i, row in enumerate(data_rows[:10]):
                journalist_row = self._create_journalist_row(row, suggested_mapping, i + 1)
                preview_data.append(journalist_row)
                
                if journalist_row.is_valid_for_import():
                    valid_count += 1
                else:
                    invalid_count += 1
            
            # Check for duplicates in user's existing data
            duplicate_count = await self._estimate_duplicates(data_rows, suggested_mapping, current_user)
            
            return ImportPreview(
                total_rows=len(data_rows),
                valid_rows=valid_count,
                invalid_rows=invalid_count,
                duplicate_rows=duplicate_count,
                field_mapping=suggested_mapping,
                sample_data=preview_data,
                detected_columns=column_names,
                suggested_mapping=suggested_mapping
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to preview file: {str(e)}"
            )
    
    async def import_journalists(
        self,
        file: UploadFile,
        field_mapping: Dict[str, str],
        current_user: User,
        skip_duplicates: bool = True,
        update_existing: bool = False
    ) -> ImportResult:
        """Import journalists with user-confirmed field mapping"""
        
        try:
            # Read and parse file
            content = await file.read()
            file_type = self._detect_file_type(file.filename)
            data_rows, _ = await self._parse_file_content(content, file_type)
            
            # Process each row
            imported_ids = []
            errors = []
            duplicate_count = 0
            success_count = 0
            
            for i, row in enumerate(data_rows):
                try:
                    journalist_row = self._create_journalist_row(row, field_mapping, i + 1)
                    
                    # Skip invalid rows
                    if not journalist_row.is_valid_for_import():
                        errors.append({
                            "row": i + 1,
                            "error": "Missing required fields (name or email)",
                            "data": journalist_row.dict()
                        })
                        continue
                    
                    # Check for duplicates
                    existing = await self._find_existing_journalist(journalist_row, current_user)
                    
                    if existing:
                        duplicate_count += 1
                        if skip_duplicates and not update_existing:
                            continue
                        elif update_existing:
                            # Update existing journalist
                            updated_journalist = await self._update_existing_journalist(
                                existing, journalist_row
                            )
                            imported_ids.append(str(updated_journalist.id))
                            success_count += 1
                        continue
                    
                    # Create new journalist
                    new_journalist = await self._create_journalist_from_row(
                        journalist_row, current_user
                    )
                    imported_ids.append(str(new_journalist.id))
                    success_count += 1
                    
                except Exception as e:
                    errors.append({
                        "row": i + 1,
                        "error": str(e),
                        "data": row
                    })
            
            return ImportResult(
                total_processed=len(data_rows),
                successfully_imported=success_count,
                failed_imports=len(errors),
                duplicates_skipped=duplicate_count,
                errors=errors,
                imported_journalist_ids=imported_ids
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Import failed: {str(e)}"
            )
    
    def _detect_file_type(self, filename: str) -> ImportFileType:
        """Detect file type from filename"""
        extension = filename.lower().split('.')[-1]
        
        if extension == 'csv':
            return ImportFileType.CSV
        elif extension in ['xlsx', 'xls']:
            return ImportFileType.EXCEL
        elif extension == 'json':
            return ImportFileType.JSON
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {extension}. Supported: CSV, Excel, JSON"
            )
    
    async def _parse_file_content(
        self, 
        content: bytes, 
        file_type: ImportFileType
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Parse file content based on type"""
        
        try:
            if file_type == ImportFileType.CSV:
                # Parse CSV
                text_content = content.decode('utf-8')
                csv_reader = csv.DictReader(StringIO(text_content))
                rows = list(csv_reader)
                columns = csv_reader.fieldnames or []
                
            elif file_type == ImportFileType.EXCEL:
                # Parse Excel
                import io
                df = pd.read_excel(io.BytesIO(content))
                rows = df.to_dict('records')
                columns = df.columns.tolist()
                
            elif file_type == ImportFileType.JSON:
                # Parse JSON
                json_content = json.loads(content.decode('utf-8'))
                
                if isinstance(json_content, list):
                    rows = json_content
                    columns = list(rows[0].keys()) if rows else []
                else:
                    raise ValueError("JSON must be an array of objects")
            
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            return rows, columns
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse file: {str(e)}"
            )
    
    def _suggest_field_mapping(self, columns: List[str]) -> Dict[str, str]:
        """Suggest field mapping based on column names"""
        mapping = {}
        
        for column in columns:
            column_lower = column.lower().strip()
            
            # Find best match for each of our fields
            for our_field, variations in self.field_mapping_suggestions.items():
                if column_lower in [v.lower() for v in variations]:
                    mapping[column] = our_field
                    break
        
        return mapping
    
    def _create_journalist_row(
        self, 
        row: Dict[str, Any], 
        field_mapping: Dict[str, str], 
        row_number: int
    ) -> JournalistImportRow:
        """Create JournalistImportRow from raw data"""
        
        journalist_data = {
            "row_number": row_number,
            "extra_data": {}
        }
        
        validation_errors = []
        
        # Map known fields
        for original_column, our_field in field_mapping.items():
            if original_column in row and row[original_column]:
                value = row[original_column]
                
                # Special handling for topics (convert string to list)
                if our_field == 'topics' and isinstance(value, str):
                    # Split by common delimiters
                    topics = re.split(r'[,;|]', value)
                    value = [t.strip() for t in topics if t.strip()]
                
                # Try to map category to our enum values
                elif our_field == 'category' and isinstance(value, str):
                    value = self._map_category_value(value)
                
                journalist_data[our_field] = value
        
        # Store unmapped fields in extra_data
        for column, value in row.items():
            if column not in field_mapping and value:
                journalist_data["extra_data"][column] = value
        
        # Validate required fields
        if not journalist_data.get("name"):
            validation_errors.append("Name is required")
        
        if not journalist_data.get("email"):
            validation_errors.append("Email is required")
        
        journalist_data["validation_errors"] = validation_errors
        journalist_data["import_status"] = "invalid" if validation_errors else "valid"
        
        return JournalistImportRow(**journalist_data)
    
    def _map_category_value(self, value: str) -> str:
        """Map category value to our enum values"""
        value_lower = value.lower().strip()
        
        category_mapping = {
            'tech': 'technology',
            'technology': 'technology',
            'business': 'business',
            'health': 'healthcare',
            'healthcare': 'healthcare',
            'medical': 'healthcare',
            'finance': 'finance',
            'financial': 'finance',
            'fintech': 'finance',
            'lifestyle': 'lifestyle',
            'entertainment': 'entertainment',
            'sports': 'sports',
            'sport': 'sports'
        }
        
        return category_mapping.get(value_lower, 'other')
    
    async def _find_existing_journalist(
        self, 
        journalist_row: JournalistImportRow, 
        current_user: User
    ) -> Optional[Journalist]:
        """Find existing journalist by email"""
        
        if not journalist_row.email:
            return None
        
        return await Journalist.find_one(
            Journalist.email == journalist_row.email,
            Journalist.added_by_user_id == str(current_user.id)
        )
    
    async def _create_journalist_from_row(
        self, 
        journalist_row: JournalistImportRow, 
        current_user: User
    ) -> Journalist:
        """Create new journalist from import row"""
        
        journalist_data = {
            "added_by_user_id": str(current_user.id),
            "name": journalist_row.name,
            "email": journalist_row.email,
            "publication": journalist_row.publication or "Unknown",
            "category": journalist_row.category or "other",
            "topics": journalist_row.topics or [],
            "country": journalist_row.country or "Unknown",
            "timezone": journalist_row.timezone or "UTC",
            "source": "imported"
        }
        
        # Add extra data as notes if present
        if journalist_row.extra_data:
            notes_parts = []
            for key, value in journalist_row.extra_data.items():
                notes_parts.append(f"{key}: {value}")
            journalist_data["notes"] = " | ".join(notes_parts)
        
        journalist = Journalist(**journalist_data)
        await journalist.create()
        
        return journalist
    
    async def _update_existing_journalist(
        self, 
        existing: Journalist, 
        journalist_row: JournalistImportRow
    ) -> Journalist:
        """Update existing journalist with new data"""
        
        # Update fields that have new data
        if journalist_row.publication:
            existing.publication = journalist_row.publication
        if journalist_row.category:
            existing.category = journalist_row.category
        if journalist_row.topics:
            existing.topics = journalist_row.topics
        if journalist_row.country:
            existing.country = journalist_row.country
        
        # Merge extra data into notes
        if journalist_row.extra_data:
            extra_notes = " | ".join([f"{k}: {v}" for k, v in journalist_row.extra_data.items()])
            if existing.notes:
                existing.notes = f"{existing.notes} | {extra_notes}"
            else:
                existing.notes = extra_notes
        
        existing.updated_at = datetime.utcnow()
        await existing.save()
        
        return existing
    
    async def _estimate_duplicates(
        self, 
        data_rows: List[Dict[str, Any]], 
        field_mapping: Dict[str, str], 
        current_user: User
    ) -> int:
        """Estimate number of duplicates in import data"""
        
        email_column = None
        for column, field in field_mapping.items():
            if field == 'email':
                email_column = column
                break
        
        if not email_column:
            return 0
        
        # Get emails from import data
        import_emails = set()
        for row in data_rows:
            if email_column in row and row[email_column]:
                import_emails.add(row[email_column].lower().strip())
        
        # Check against existing journalists
        duplicate_count = 0
        for email in import_emails:
            existing = await Journalist.find_one(
                Journalist.email == email,
                Journalist.added_by_user_id == str(current_user.id)
            )
            if existing:
                duplicate_count += 1
        
        return duplicate_count

# Global import service instance
import_service = ImportService()
