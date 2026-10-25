"""Identity resolution engine for HackerRank Orchestrate - Ghost Data Still Exists.

Resolves current and historical user identities from user_identities.csv and user_audit_log.csv.
"""

import pandas as pd
from typing import Dict, Set, Optional, Any

class IdentityResolver:
    def __init__(self, identities_csv_path: str, audit_log_csv_path: str):
        self.identities_df = pd.read_csv(identities_csv_path)
        self.audit_log_df = pd.read_csv(audit_log_csv_path)
        self._build_indexes()

    def _build_indexes(self):
        self.user_to_profile: Dict[str, Dict[str, Any]] = {}
        self.email_to_user: Dict[str, str] = {}
        self.phone_to_user: Dict[str, str] = {}
        self.hash_to_user: Dict[str, str] = {}
        self.name_to_users: Dict[str, Set[str]] = {}

        # 1. Base identities
        for _, row in self.identities_df.iterrows():
            uid = str(row['user_id']).strip()
            email = str(row['email']).strip().lower() if pd.notna(row['email']) else ""
            phone = str(row['phone']).strip() if pd.notna(row['phone']) else ""
            ehash = str(row['email_hash']).strip().lower() if pd.notna(row['email_hash']) else ""
            name = str(row['name']).strip() if pd.notna(row['name']) else ""
            updated_at = str(row['updated_at']).strip() if pd.notna(row['updated_at']) else ""

            self.user_to_profile[uid] = {
                'user_id': uid,
                'name': name,
                'current_email': email,
                'emails': {email} if email else set(),
                'current_phone': phone,
                'phones': {phone} if phone else set(),
                'current_hash': ehash,
                'hashes': {ehash} if ehash else set(),
                'names': {name.lower()} if name else set(),
                'updated_at': updated_at
            }

            if email:
                self.email_to_user[email] = uid
            if phone:
                self.phone_to_user[phone] = uid
            if ehash:
                self.hash_to_user[ehash] = uid
            if name:
                self.name_to_users.setdefault(name.lower(), set()).add(uid)

        # 2. Historical identity changes from audit log
        for _, row in self.audit_log_df.iterrows():
            uid = str(row['user_id']).strip()
            if uid not in self.user_to_profile:
                self.user_to_profile[uid] = {
                    'user_id': uid,
                    'name': "",
                    'current_email': "",
                    'emails': set(),
                    'current_phone': "",
                    'phones': set(),
                    'current_hash': "",
                    'hashes': set(),
                    'names': set(),
                    'updated_at': ""
                }
            
            field = str(row['field_name']).strip()
            old_val = str(row['old_value']).strip() if pd.notna(row['old_value']) else ""
            new_val = str(row['new_value']).strip() if pd.notna(row['new_value']) else ""

            if field == 'email':
                if old_val:
                    val_lower = old_val.lower()
                    self.user_to_profile[uid]['emails'].add(val_lower)
                    self.email_to_user[val_lower] = uid
                if new_val:
                    val_lower = new_val.lower()
                    self.user_to_profile[uid]['emails'].add(val_lower)
                    self.email_to_user[val_lower] = uid
            elif field == 'phone':
                if old_val:
                    self.user_to_profile[uid]['phones'].add(old_val)
                    self.phone_to_user[old_val] = uid
                if new_val:
                    self.user_to_profile[uid]['phones'].add(new_val)
                    self.phone_to_user[new_val] = uid
            elif field == 'email_hash':
                if old_val:
                    val_lower = old_val.lower()
                    self.user_to_profile[uid]['hashes'].add(val_lower)
                    self.hash_to_user[val_lower] = uid
                if new_val:
                    val_lower = new_val.lower()
                    self.user_to_profile[uid]['hashes'].add(val_lower)
                    self.hash_to_user[val_lower] = uid
            elif field == 'name':
                if old_val:
                    self.user_to_profile[uid]['names'].add(old_val.lower())
                if new_val:
                    self.user_to_profile[uid]['names'].add(new_val.lower())

    def get_user_id(self, email_or_identifier: str) -> Optional[str]:
        target = email_or_identifier.strip().lower()
        if target in self.email_to_user:
            return self.email_to_user[target]
        if target in self.hash_to_user:
            return self.hash_to_user[target]
        if email_or_identifier.strip() in self.phone_to_user:
            return self.phone_to_user[email_or_identifier.strip()]
        if email_or_identifier.strip() in self.user_to_profile:
            return email_or_identifier.strip()
        return None

    def get_all_identifiers(self, user_id: str) -> Dict[str, Any]:
        return self.user_to_profile.get(user_id, {
            'user_id': user_id,
            'emails': set(),
            'phones': set(),
            'hashes': set(),
            'names': set()
        })
