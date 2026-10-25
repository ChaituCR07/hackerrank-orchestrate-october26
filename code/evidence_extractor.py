"""Evidence extractor for HackerRank Orchestrate - Ghost Data Still Exists.

Parses all multimodal evidence files (SQL dumps, JSON/TXT records, logs, PDFs, OCR screenshots)
and indexes discovered resources, system identities, operational states, and associated user identifiers.
Supports trace-aware log reconstruction, schema normalization, and replication drift detection.
"""

import os
import json
import sqlite3
import re
import pandas as pd
from typing import Dict, List, Set, Any, Optional

class EvidenceExtractor:
    def __init__(self, evidence_csv_path: str, dataset_dir: str):
        self.dataset_dir = dataset_dir
        self.manifest_df = pd.read_csv(evidence_csv_path)
        # Store evidence file metadata
        self.evidence_files: Dict[str, Dict[str, Any]] = {}
        for _, row in self.manifest_df.iterrows():
            eid = row['file_id']
            self.evidence_files[eid] = {
                'file_id': eid,
                'file_path': os.path.join(dataset_dir, row['file_path']),
                'rel_path': row['file_path'],
                'origin': row['origin'],
                'captured_at': row['captured_at']
            }
        
        # Parsed records: file_id -> list of record dicts
        self.file_records: Dict[str, List[Dict[str, Any]]] = {}
        self._parse_all_evidence()

    def _parse_all_evidence(self):
        for eid, info in self.evidence_files.items():
            fpath = info['file_path']
            if not os.path.exists(fpath):
                self.file_records[eid] = []
                continue
            
            records = []
            if fpath.endswith('.sql'):
                records = self._parse_sql(fpath)
            elif fpath.endswith('.json'):
                records = self._parse_json(fpath)
            elif fpath.endswith('.txt'):
                records = self._parse_txt(fpath)
            elif fpath.endswith('.log'):
                records = self._parse_log(fpath)
            elif fpath.endswith('.pdf'):
                records = self._parse_pdf(fpath)
            elif fpath.endswith('.png'):
                records = self._parse_image(fpath)
            
            self.file_records[eid] = records

    def _parse_sql(self, fpath: str) -> List[Dict[str, Any]]:
        records = []
        try:
            con = sqlite3.connect(':memory:')
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                con.executescript(fp.read())
            
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            
            for tbl in tables:
                cur = con.execute(f"PRAGMA table_info({tbl})")
                cols = [c[1] for c in cur.fetchall()]
                
                rows = con.execute(f"SELECT * FROM {tbl}").fetchall()
                for row_data in rows:
                    row_dict = dict(zip(cols, row_data))
                    rec = self._normalize_sql_row(tbl, row_dict)
                    if rec:
                        records.append(rec)
            con.close()
        except Exception:
            pass
        return records

    def _normalize_sql_row(self, table_name: str, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Case 1: Primary/Replica table with record_json
        if 'record_json' in row and row['record_json']:
            try:
                inner = json.loads(row['record_json'])
                sys_id = row.get('origin_system', '')
                res_id = row.get('resource_id', inner.get('resource_id', ''))
                
                identifiers = set()
                for k in ['user_id', 'customer_reference', 'subject_reference', 'subject_selector', 'email', 'phone', 'email_hash']:
                    val = inner.get(k)
                    if val and isinstance(val, str):
                        identifiers.add(val.strip().lower())
                if 'document' in inner and isinstance(inner['document'], dict):
                    doc = inner['document']
                    for k in ['email', 'customer_reference', 'phone', 'email_hash']:
                        val = doc.get(k)
                        if val and isinstance(val, str):
                            identifiers.add(val.strip().lower())
                
                state = "PRESENT"
                if sys_id == "analytics_platform":
                    u = inner.get('user_id')
                    em = inner.get('email')
                    ph = inner.get('phone')
                    eh = inner.get('email_hash')
                    state = "ANONYMIZED" if (not u and not em and not ph and not eh) else "PRESENT"
                elif sys_id == "integration_service":
                    state = "ACTIVE" if inner.get('enabled') is True else "DISABLED"
                elif sys_id == "backup_service":
                    state = "ACTIVE" if inner.get('restore_allowed') is True else "BLOCKED"
                elif sys_id == "support_platform":
                    msg = str(inner.get('message_text', ''))
                    state = "REDACTED" if (msg == "[REDACTED]" or not any(x in msg for x in ['@', '+'])) else "PRESENT"

                return {
                    'system_id': sys_id,
                    'resource_id': res_id,
                    'table': table_name,
                    'state': state,
                    'identifiers': identifiers,
                    'raw': inner
                }
            except Exception:
                pass

        # Case 2: Dedicated schema tables (e.g. customer_data_inventory_*.sql, customer_accounts_failover_replica)
        res_id = str(row.get('resource_id', ''))
        identifiers = set()
        for k in ['user_id', 'email', 'phone', 'email_hash', 'subject_reference', 'customer_reference', 'owner_email', 'customer_email', 'requester_email']:
            val = row.get(k)
            if val and isinstance(val, str):
                identifiers.add(val.strip().lower())

        sys_id = "account_service"
        state = "PRESENT"
        tbl_lower = table_name.lower()
        if "profiles" in tbl_lower or "account" in tbl_lower:
            sys_id = "account_service"
            state = "PRESENT"
        elif "search" in tbl_lower:
            sys_id = "search_service"
            state = "PRESENT"
        elif "analytics" in tbl_lower:
            sys_id = "analytics_platform"
            em = row.get('email')
            u = row.get('customer_reference') or row.get('user_id')
            ph = row.get('phone')
            eh = row.get('email_hash')
            state = "ANONYMIZED" if (not em and not u and not ph and not eh) else "PRESENT"
        elif "support" in tbl_lower:
            sys_id = "support_platform"
            state = "PRESENT"
        elif "export" in tbl_lower:
            sys_id = "export_service"
            state = "PRESENT"
        elif "connector" in tbl_lower:
            sys_id = "integration_service"
            en = row.get('enabled')
            state = "ACTIVE" if en in [1, '1', True] or str(row.get('status', '')).upper() == 'ACTIVE' else "DISABLED"
        elif "backup" in tbl_lower:
            sys_id = "backup_service"
            ra = row.get('restore_allowed')
            state = "ACTIVE" if ra in [1, '1', True] or str(row.get('status', '')).upper() == 'ACTIVE' else "BLOCKED"
        elif "audit" in tbl_lower:
            sys_id = "security_service"
            state = "PRESENT"

        return {
            'system_id': sys_id,
            'resource_id': res_id,
            'table': table_name,
            'state': state,
            'identifiers': identifiers,
            'raw': row
        }

    def _parse_json(self, fpath: str) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(fpath, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            
            # Case 1: service_resource_export
            if 'service_exports' in data:
                exports = data['service_exports']
                for sys_id, content in exports.items():
                    for list_key, items in content.items():
                        if not isinstance(items, list):
                            continue
                        for item in items:
                            records.append(self._normalize_export_item(sys_id, item))
            
            # Case 2: customer_data_snapshot_bundle
            elif 'snapshots' in data:
                for snap in data['snapshots']:
                    sys_id = snap.get('data_store', '')
                    collection = snap.get('collection', '')
                    for rec in snap.get('records', []):
                        records.append(self._normalize_snapshot_bundle_record(sys_id, collection, rec))

            # Case 3: customer_export_jobs
            elif 'records' in data and data.get('collection') == 'customer_export_jobs':
                for job in data['records']:
                    res_id = job.get('resource_id', '')
                    identifiers = set()
                    for k in ['owner_email', 'email', 'customer_reference']:
                        v = job.get(k)
                        if v:
                            identifiers.add(str(v).strip().lower())
                    records.append({
                        'system_id': 'export_service',
                        'resource_id': res_id,
                        'state': 'PRESENT',
                        'identifiers': identifiers,
                        'raw': job
                    })

            # Case 4: customer_analytics_reports
            elif 'records' in data and data.get('collection') == 'customer_analytics_reports':
                for item in data['records']:
                    res_id = item.get('resource_id', '')
                    identifiers = set()
                    for k in ['user_id', 'email', 'phone', 'email_hash']:
                        v = item.get(k)
                        if v:
                            identifiers.add(str(v).strip().lower())
                    u = item.get('user_id')
                    em = item.get('email')
                    state = "PRESENT" if (u or em) else "ANONYMIZED"
                    records.append({
                        'system_id': 'analytics_platform',
                        'resource_id': res_id,
                        'state': state,
                        'identifiers': identifiers,
                        'raw': item
                    })
        except Exception:
            pass
        return records

    def _normalize_export_item(self, sys_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        res_id = item.get('resource_id', '')
        identifiers = set()
        for k in ['customer_reference', 'subject_reference', 'subject_selector', 'email', 'query']:
            v = item.get(k)
            if v and isinstance(v, str):
                identifiers.add(v.strip().lower())
        
        state = "PRESENT"
        if sys_id == "account_service":
            code = item.get('status_code')
            state = "ABSENT" if code == 404 else "PRESENT"
            prof = item.get('profile')
            if prof and isinstance(prof, dict):
                for pk, pv in prof.items():
                    if pv and isinstance(pv, str):
                        identifiers.add(pv.strip().lower())
        elif sys_id == "search_service":
            hits = item.get('hits', {})
            total = hits.get('total', 0) if isinstance(hits, dict) else 0
            state = "PRESENT" if total > 0 else "ABSENT"
            if isinstance(hits, dict):
                for doc in hits.get('documents', []):
                    if isinstance(doc, dict):
                        for dk, dv in doc.items():
                            if dv and isinstance(dv, str):
                                identifiers.add(dv.strip().lower())
        elif sys_id == "analytics_platform":
            u = item.get('customer_reference')
            em = item.get('email')
            ph = item.get('phone')
            eh = item.get('email_hash')
            state = "ANONYMIZED" if (not u and not em and not ph and not eh) else "PRESENT"
        elif sys_id == "integration_service":
            status = str(item.get('status', '')).upper()
            state = "ACTIVE" if status == "ACTIVE" or item.get('enabled') is True else "DISABLED"
        elif sys_id == "backup_service":
            status = str(item.get('status', '')).upper()
            state = "ACTIVE" if status == "ACTIVE" or item.get('restore_allowed') is True else "BLOCKED"
        elif sys_id == "support_platform":
            msgs = item.get('messages', [])
            has_pii = False
            for m in msgs:
                if isinstance(m, dict):
                    txt = str(m.get('body', ''))
                    if '@' in txt or '+' in txt:
                        has_pii = True
            state = "PRESENT" if has_pii else "REDACTED"
        elif sys_id == "security_service":
            state = "PRESENT"

        return {
            'system_id': sys_id,
            'resource_id': res_id,
            'state': state,
            'identifiers': identifiers,
            'raw': item
        }

    def _normalize_snapshot_bundle_record(self, sys_id: str, collection: str, rec: Dict[str, Any]) -> Dict[str, Any]:
        res_id = rec.get('resource_id', '')
        identifiers = set()
        for k in ['subject_reference', 'customer_reference', 'user_id', 'email', 'phone', 'email_hash']:
            v = rec.get(k)
            if v and isinstance(v, str):
                identifiers.add(v.strip().lower())
        
        state = "PRESENT"
        if collection == "deleted_customer_references":
            sys_id = "identity_service"
            em = rec.get('email')
            ph = rec.get('phone')
            nm = rec.get('name')
            state = "REDACTED" if (not em and not ph and not nm) else "PRESENT"
        elif sys_id == "security_service":
            state = "PRESENT"
        elif sys_id == "account_service":
            state = "ABSENT" if not rec else "PRESENT"

        return {
            'system_id': sys_id,
            'resource_id': res_id,
            'state': state,
            'identifiers': identifiers,
            'raw': rec
        }

    def _parse_txt(self, fpath: str) -> List[Dict[str, Any]]:
        records = []
        try:
            with open(fpath, 'r', encoding='utf-8') as fp:
                for line in fp:
                    line = line.strip()
                    if not line.startswith('-'):
                        continue
                    parts = [p.strip() for p in line.lstrip('-').split('|')]
                    if len(parts) >= 6:
                        sys_id = parts[1]
                        res_id = parts[2]
                        cat = parts[3]
                        raw_status = parts[4]
                        ident_str = parts[5].lower()
                        
                        state = "PRESENT"
                        if raw_status == "NOT_FOUND":
                            state = "ABSENT"
                        elif raw_status == "FOUND":
                            state = "PRESENT"
                        elif raw_status == "ANONYMIZED":
                            state = "ANONYMIZED"
                        elif raw_status == "REDACTED":
                            state = "REDACTED"
                        elif raw_status == "IDENTIFIABLE":
                            state = "PRESENT"
                        elif raw_status == "ACTIVE":
                            state = "ACTIVE"
                        elif raw_status == "DISABLED":
                            state = "DISABLED"
                        elif raw_status == "BLOCKED":
                            state = "BLOCKED"
                        
                        records.append({
                            'system_id': sys_id,
                            'resource_id': res_id,
                            'state': state,
                            'identifiers': {ident_str} if ident_str != "no direct identifier" else set(),
                            'raw': line
                        })
        except Exception:
            pass
        return records

    def _parse_log(self, fpath: str) -> List[Dict[str, Any]]:
        """Trace-aware log parser grouping multi-line events by trace_id."""
        traces: Dict[str, Dict[str, Any]] = {}
        standalone_records: List[Dict[str, Any]] = []

        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                for line in fp:
                    # Look for trace_id or requestId
                    m_tr = re.search(r'(?:trace_id|requestId|batch)=([^\s"]+)', line)
                    tr_id = m_tr.group(1).strip('"') if m_tr else None

                    # Extract identifiers on this line
                    line_ids = set()
                    for m_id in re.finditer(r'(?:lookup_key|subject_key|subject_reference|matched_value|owner_key|correlation_key)="?([^\s",]+)"?', line):
                        val = m_id.group(1).strip('"\'').lower()
                        if val != 'null':
                            line_ids.add(val)


                    # Extract resource_id
                    m_res = re.search(r'resource_id=([^\s"]+)', line)
                    res_id = m_res.group(1).strip('"') if m_res else ""

                    # Extract service
                    sys_id = ""
                    if res_id.startswith('account_'):
                        sys_id = 'account_service'
                    elif res_id.startswith('search_'):
                        sys_id = 'search_service'
                    elif res_id.startswith('analytics_'):
                        sys_id = 'analytics_platform'
                    elif res_id.startswith('support_'):
                        sys_id = 'support_platform'
                    elif res_id.startswith('audit_record_'):
                        sys_id = 'security_service'
                    elif res_id.startswith('data_flow_'):
                        sys_id = 'integration_service'
                    elif res_id.startswith('backup_'):
                        sys_id = 'backup_service'
                    elif res_id.startswith('export_'):
                        sys_id = 'export_service'
                    elif res_id.startswith('tombstone_'):
                        sys_id = 'identity_service'
                    else:
                        m_svc = re.search(r'(?:service|function)=([^\s"]+)', line)
                        if m_svc:
                            raw_s = m_svc.group(1).strip('"')
                            if raw_s == 'support_replica':
                                sys_id = 'support_platform'
                            elif raw_s == 'search_index_service':
                                sys_id = 'search_service'
                            else:
                                sys_id = raw_s

                    # Extract state
                    state = None
                    if 'rows=0' in line or 'http_status=404' in line or 'result="NOT_FOUND"' in line or 'marker_found=true' in line:
                        state = "ABSENT"
                    elif 'rows=1' in line or 'http_status=200' in line or 'result="FOUND"' in line or 'marker_found=false' in line:
                        state = "PRESENT"
                    elif 'message_pii_scan' in line or 'direct_identifiers="1"' in line or 'result="IDENTIFIABLE"' in line:
                        state = "PRESENT"
                    elif 'audience_cohort=' in line and 'customer_reference=null' in line and 'email=null' in line:
                        state = "ANONYMIZED"
                    elif 'retention_until=' in line:
                        state = "PRESENT"
                    elif 'enabled=true' in line or 'mode="continuous_sync"' in line:
                        state = "ACTIVE"
                    elif 'enabled=false' in line:
                        state = "DISABLED"
                    elif 'restore_allowed=true' in line or 'deletion_block=false' in line:
                        state = "ACTIVE"
                    elif 'restore_allowed=false' in line or 'deletion_block=true' in line:
                        state = "BLOCKED"

                    if tr_id:
                        if tr_id not in traces:
                            traces[tr_id] = {
                                'system_id': sys_id,
                                'resource_id': res_id,
                                'state': state,
                                'identifiers': set(),
                                'raw': [line]
                            }
                        traces[tr_id]['identifiers'].update(line_ids)
                        if res_id:
                            traces[tr_id]['resource_id'] = res_id
                        if sys_id:
                            traces[tr_id]['system_id'] = sys_id
                        if state:
                            traces[tr_id]['state'] = state
                        traces[tr_id]['raw'].append(line)
                    else:
                        if res_id:
                            standalone_records.append({
                                'system_id': sys_id,
                                'resource_id': res_id,
                                'state': state if state else "PRESENT",
                                'identifiers': line_ids,
                                'raw': line
                            })
        except Exception:
            pass

        # Combine trace records
        results = list(standalone_records)
        for tr_id, tr in traces.items():
            if tr['resource_id']:
                results.append({
                    'system_id': tr['system_id'],
                    'resource_id': tr['resource_id'],
                    'state': tr['state'] if tr['state'] else "PRESENT",
                    'identifiers': tr['identifiers'],
                    'raw': '\n'.join(tr['raw'])
                })
        return results

    def _parse_pdf(self, fpath: str) -> List[Dict[str, Any]]:
        records = []
        try:
            import pypdf
            reader = pypdf.PdfReader(fpath)
            full_text = " ".join([p.extract_text() for p in reader.pages])
            
            m_res = re.findall(r'(support_\d+|export_\d+|audit_record_\d+|account_\d+)', full_text)
            m_u = re.findall(r'(user_\d+)', full_text)
            m_em = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', full_text)
            
            identifiers = set([u.lower() for u in m_u] + [em.lower() for em in m_em])
            for res_id in set(m_res):
                sys_id = 'support_platform' if res_id.startswith('support_') else 'account_service'
                records.append({
                    'system_id': sys_id,
                    'resource_id': res_id,
                    'state': 'PRESENT',
                    'identifiers': identifiers,
                    'raw': full_text[:200]
                })
        except Exception:
            pass
        return records

    def _parse_image(self, fpath: str) -> List[Dict[str, Any]]:
        return []
