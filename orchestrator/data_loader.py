import os
import io
import pandas as pd
import requests
from typing import Dict, Any, Tuple

DS2_URL = "https://docs.google.com/spreadsheets/d/1kApKRPgaVH0qlaKA-J0l2Yy5L2KmdaR7/export?format=csv"
DS3_URL = "https://docs.google.com/spreadsheets/d/1krL9KbJOjBpbsS7DXrVgRZgsiWkhrmD2HF8NOp_JzJ8/export?format=csv"
DS4_URL = "https://docs.google.com/spreadsheets/d/1JF7Hh7DDCx9XieL4U4EoJLPQtdDxctl7wZYbfvAwb5I/export?format=csv"
DS5_URL = "https://docs.google.com/spreadsheets/d/1bTB2AXhoydP282fWPxoFt9nZ8rj5iI3DSzpKQ9Cu194/export?format=csv"

def fetch_csv(url: str) -> pd.DataFrame:
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return pd.DataFrame()

import json
import re

def evaluate_ds0(mcat_val: Any) -> Tuple[str, str, list]:
    try:
        # Sanitize input to prevent [Errno 22] on Windows URLs
        mcat_clean = str(mcat_val).strip().replace("\n", "").replace("\r", "")
        url1 = f"https://get-presigned-url-for-mcat-w2yrp7i6za-el.a.run.app/?mcat_id={mcat_clean}"
        headers = {"Token": "adr-wsbu-ocm"}
        r1 = requests.get(url1, headers=headers, timeout=20)
        
        if r1.status_code == 200:
            item = r1.json()
            link = None
            try:
                link = item.get('finalized_specs', {}).get('file_info', {}).get('url')
            except: pass
            
            if not link:
                try:
                    file_info = item.get('finalized_specs', {}).get('file_info')
                    if isinstance(file_info, list) and len(file_info) > 0:
                        link = file_info[0].get('url', file_info[0].get('download_url'))
                except: pass
            
            if not link:
                json_str = json.dumps(item)
                m = re.search(r'https://storage\.googleapis\.com/[^\s"\']+', json_str)
                if m: link = m.group(0)
            
            if not link:
                link = item.get("url") or r1.text.strip('"')

            if link and "http" in link:
                # Sanitize link just in case
                link = link.strip().replace("\n", "").replace("\r", "")
                r2 = requests.get(link, timeout=60)
                if r2.status_code == 200:
                    try:
                        data = r2.json()
                        if isinstance(data, dict): data = [data]
                        specs = []
                        if isinstance(data, list):
                            for item in data:
                                fs_block = item.get('finalized_specs', {})
                                for key in ['finalized_primary_specs', 'finalized_secondary_specs', 'finalized_tertiary_specs']:
                                    group = fs_block.get(key, {})
                                    tier_name = key.replace('finalized_', '').replace('_specs', '').capitalize()
                                    if isinstance(group, dict):
                                        for s in group.get('specs', []):
                                            opts = s.get('options', [])
                                            if opts and isinstance(opts, list):
                                                specs.append({
                                                    'spec_name': s.get('spec_name', ''), 
                                                    'spec_options': opts[:6],
                                                    'tier': tier_name
                                                })
                        
                        return "LOADED", f"Platform baseline loaded ({len(specs)} specs)", specs
                    except: pass
    except Exception as e:
        print(f"Error in evaluate_ds0: {e}")
    return "LOADED", "No platform baseline found", []


def evaluate_ds1(mcat_val: Any) -> Tuple[str, str, list]:
    try:
        # Sanitize input to prevent [Errno 22] on Windows URLs
        mcat_clean = str(mcat_val).strip().replace("\n", "").replace("\r", "")
        url = f"https://get-buyer-isq-details-w2yrp7i6za-el.a.run.app/?mcat_id={mcat_clean}"
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            item = r.json()
            data = item[0] if isinstance(item, list) and len(item) > 0 else item
            link = None
            try:
                root_files = data.get('steps', {}).get('step_11_normalizer_output', {}).get('root_files', [])
                for f in root_files:
                    if f.get('filename') == 'updated_spec_value_counts_cumulative.csv':
                        link = f.get('url')
                        break
            except Exception as e:
                print(f"Error parsing root_files for mcat_id {mcat_clean}: {e}")
            
            if not link:
                try:
                    stats = data.get('normalization', {}).get('final_stats', [])
                    for f in stats:
                        if f.get('filename') == 'final_spec_value_counts_cumulative.csv': link = f.get('url'); break
                except Exception as e:
                    print(f"Error parsing final_stats for mcat_id {mcat_clean}: {e}")
            
            if link:
                # Sanitize link
                link = link.strip().replace("\n", "").replace("\r", "")
                df = fetch_csv(link)
                if not df.empty:
                    grouped = {}
                    for _, row in df.iterrows():
                        spec = str(row.get('normalised_spec_name', '')).strip()
                        if not spec or spec == 'nan': continue
                        if spec not in grouped:
                            grouped[spec] = {'spec_name': spec, 'total_product_count': 0, 'option_map': {}}
                        count = 0
                        try: count = float(row.get('prod_count', 0))
                        except: pass
                        grouped[spec]['total_product_count'] += count
                        val = str(row.get('normalised_spec_value', '')).strip()
                        if val == 'nan': val = ''
                        unit = str(row.get('normalised_spec_value_unit', '')).strip()
                        if unit and unit != 'nan': val = f"{val} {unit}".strip()
                        if not val: continue
                        if val not in grouped[spec]['option_map']: grouped[spec]['option_map'][val] = 0
                        grouped[spec]['option_map'][val] += count
                        
                    buyer_specs = []
                    for name, d in grouped.items():
                        sorted_opts = sorted(d['option_map'].items(), key=lambda x: x[1], reverse=True)
                        total = d['total_product_count']
                        selected = [o[0] for o in sorted_opts if o[1] >= 2][:10]
                        if total > 0:
                            buyer_specs.append({'spec_name': name, 'total_product_count': total, 'example_values': selected})
                    
                    buyer_specs.sort(key=lambda x: x['total_product_count'], reverse=True)
                    if buyer_specs:
                        return "RICH", f"{len(buyer_specs)} buyer specs found", buyer_specs[:10]
                else:
                    print(f"Fetched CSV from {link} was empty for mcat_id {mcat_clean}")
            else:
                print(f"No valid link found for mcat_id {mcat_clean} in evaluate_ds1")
        else:
            print(f"API call to {url} failed with status code {r.status_code} for mcat_id {mcat_clean}")
    except Exception as e:
        print(f"An error occurred in evaluate_ds1 for mcat_id {mcat_val}: {e}")
    return "EMPTY", "No buyer signals", []


def evaluate_ds2(mcat_val: Any) -> Tuple[str, str, list]:
    df = fetch_csv(DS2_URL)
    mcat_target = str(mcat_val).strip().replace(".0", "")
    if not df.empty and 'mcat_id' in df.columns:
        df['mcat_id_str'] = df['mcat_id'].astype(str).str.replace(".0", "", regex=False).str.strip()
        filtered = df[df['mcat_id_str'] == mcat_target]
        if not filtered.empty:
            results = []
            for _, row in filtered.iterrows():
                # NEW: Handle "Missing Spec" JSON column from blueprint
                missing_json = row.get("Missing Spec")
                if missing_json and isinstance(missing_json, str) and str(missing_json).strip().startswith("["):
                    try:
                        import json
                        parsed_specs = json.loads(missing_json)
                        for ps in parsed_specs:
                            results.append({
                                "spec_name": ps.get("spec_name"),
                                "sample_values": ps.get("options", []),
                                "source": "custom_specs_json"
                            })
                        continue # Skip standard parsing if JSON found
                    except: pass
                
                # FALLBACK: Standard row-based parsing
                s_name = str(row.get('spec_name', row.get('Spec Name', ''))).strip()
                v = str(row.get('option_value', row.get('options', ''))).strip()
                if s_name and s_name.lower() != 'nan':
                    results.append({
                        "spec_name": s_name,
                        "sample_values": [v] if v and v.lower() != 'nan' else [],
                        "source": "custom_specs_flat"
                    })
            
            if results:
                return "RICH", f"{len(results)} custom candidates discovered", results
    return "EMPTY", "No custom specs", []


def evaluate_ds3(mcat_val: Any) -> Tuple[str, str, list]:
    df = fetch_csv(DS3_URL)
    mcat_target = str(mcat_val).strip().replace(".0", "")
    if not df.empty and 'mcat_id' in df.columns:
        # Convert column to string and remove .0 to ensure match
        df['mcat_id_str'] = df['mcat_id'].astype(str).str.replace(".0", "", regex=False).str.strip()
        filtered = df[df['mcat_id_str'] == mcat_target]
        if not filtered.empty:
            grouped = {}
            total_mcat_impressions = 0
            for _, row in filtered.iterrows():
                # Flexible column detection for Spec Name/Option
                spec = str(row.get('Spec Name', row.get('spec_name', row.get('Keyword', '')))).strip().lower()
                opt = str(row.get('Spec Option', row.get('spec_option', row.get('Option', '')))).strip()
                
                # Fetch impression (handle variants)
                try: 
                    imp = float(row.get('impression', row.get('total_impressions', row.get('Impression', 0))))
                except: 
                    imp = 0
                
                if not spec or not opt: continue
                
                if spec not in grouped: grouped[spec] = {'total_impressions': 0, 'options': {}}
                grouped[spec]['total_impressions'] += imp
                if opt not in grouped[spec]['options']: grouped[spec]['options'][opt] = 0
                grouped[spec]['options'][opt] += imp
                
                total_mcat_impressions += imp
            
            specs = []
            for name, d in grouped.items():
                sorted_o = sorted(d['options'].items(), key=lambda x: x[1], reverse=True)
                specs.append({
                    'spec_name': name, 
                    'total_impressions': d['total_impressions'], 
                    'spec_options': [o[0] for o in sorted_o][:10]
                })
            
            specs.sort(key=lambda x: x['total_impressions'], reverse=True)
            
            # Status Logic based on Sum
            if total_mcat_impressions > 50: status = "RICH"
            elif total_mcat_impressions > 0: status = "SPARSE"
            else: status = "EMPTY"
                
            return status, f"Total MCAT search impressions: {int(total_mcat_impressions)}", specs[:10]
            
    return "EMPTY", "No search data found for this MCAT", []
    
def evaluate_ds5(mcat_val: Any) -> Tuple[str, str, list]:
    df = fetch_csv(DS5_URL)
    mcat_target = str(mcat_val).strip().replace(".0", "")
    if not df.empty and 'mcat_id' in df.columns:
        df['mcat_id_str'] = df['mcat_id'].astype(str).str.replace(".0", "", regex=False).str.strip()
        filtered = df[df['mcat_id_str'] == mcat_target]
        if not filtered.empty:
            return "LOADED", f"{len(filtered)} records found in option fill rate", filtered.to_dict('records')
    return "EMPTY", "No option fill rate data", []


def evaluate_ds4(mcat_val: Any) -> Tuple[str, str, list]:
    df = fetch_csv(DS4_URL)
    mcat_target = str(mcat_val).strip().replace(".0", "")
    if not df.empty and 'mcat_id' in df.columns:
        df['mcat_id_str'] = df['mcat_id'].astype(str).str.replace(".0", "", regex=False).str.strip()
        filtered = df[df['mcat_id_str'] == mcat_target]
        if not filtered.empty:
            return "RICH", f"{len(filtered)} fill rate records found", filtered.to_dict('records')
