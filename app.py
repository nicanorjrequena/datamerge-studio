"""DataMerge Studio: upload, read-only output preview, and export."""
import hashlib
import json
import pandas as pd
import streamlit as st
from src.simple_workflow import inspect_uploads, prepare_output, master_excel_bytes
from src.engine import worksheets

MERGE_FAVICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44">
<defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#237c62"/><stop offset="1" stop-color="#124b3c"/></linearGradient></defs>
<rect width="44" height="44" rx="13" fill="url(#g)"/>
<g transform="translate(6 8)" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
<path d="M3 14H11M7 9L12 14L7 19" stroke="#E7FFF3"/>
<path d="M29 14H21M25 9L20 14L25 19" stroke="#A3E7C7"/>
<rect x="14.5" y="7" width="3" height="14" rx="1.5" fill="white" stroke="none"/>
</g></svg>'''
st.set_page_config(page_title='DataMerge Studio', page_icon=MERGE_FAVICON, layout='wide')
st.markdown('''<style>
:root{--datamerge-font:"Inter","Segoe UI Variable","Segoe UI",-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif}
html,body,[data-testid="stApp"],.stApp,input,textarea,button,select{font-family:var(--datamerge-font)!important}
[data-testid="stApp"] p,[data-testid="stApp"] label,[data-testid="stApp"] h1,[data-testid="stApp"] h2,[data-testid="stApp"] h3,[data-testid="stApp"] h4{font-family:var(--datamerge-font)!important}
h1{font-weight:750!important;letter-spacing:-1.5px!important;line-height:1.15!important}
h2,h3{font-weight:650!important;letter-spacing:-.6px!important}
[data-testid="stSidebar"] [role="radiogroup"] label{font-size:14px;font-weight:500;letter-spacing:-.15px}
.block-container{max-width:1250px;padding-top:2.5rem}
[data-testid="stSidebar"]{background:#edf3ef;border-right:1px solid #dce5df}
[data-testid="stSidebar"] .sidebar-brand{display:flex;align-items:center;gap:12px;margin:12px 0 38px;color:#183d33}
.merge-icon{display:flex;align-items:center;justify-content:center;width:44px;height:44px;flex:0 0 44px;border-radius:13px;background:linear-gradient(145deg,#237c62,#124b3c);box-shadow:0 4px 12px #153f3420,inset 0 1px 0 #ffffff28}
.brand-name{font-size:20px;font-weight:700;letter-spacing:-.6px;line-height:1.1}
.brand-subtitle{margin-top:5px;font-size:10px;font-weight:600;letter-spacing:2.4px;text-transform:uppercase;color:#678276}
[data-testid="stSidebar"] [data-testid="stRadio"] > label{color:#456359;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:15px}
[data-testid="stSidebar"] [role="radiogroup"]{gap:7px}
[data-testid="stSidebar"] [role="radiogroup"] label{border-radius:8px;padding:12px 15px;margin:0;transition:background .15s,color .15s;color:#4c695f;cursor:pointer}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child{position:absolute;opacity:0;width:0;overflow:hidden}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#dce8e0;color:#173e32}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#17634c;color:white;box-shadow:0 3px 8px #173e3210}
[data-testid="stSidebar"] [role="radiogroup"] label:focus-within{outline:2px solid #75a68d;outline-offset:2px}
</style>''', unsafe_allow_html=True)
if st.session_state.get('workspace_revision') != 3:
    st.session_state.clear()
    st.session_state.update(workspace_revision=3, selected_inputs=[])

st.session_state.setdefault('column_changes', [])
st.session_state.setdefault('sheet_choices', {})
st.session_state.setdefault('edit_revision', 0)
st.session_state.setdefault('upload_revision', 0)
upload_key = f'datasets-{st.session_state.upload_revision}'


def clear_data() -> None:
    """Reset this user's uploaded files and all derived session state."""
    next_upload = st.session_state.upload_revision + 1
    st.session_state.clear()
    st.session_state.update(workspace_revision=3, selected_inputs=[],
                            upload_revision=next_upload, workspace_page='Upload')


def navigate(page: str) -> None:
    st.session_state.workspace_page = page


def save_change(change: dict, sources: list) -> None:
    try:
        prepare_output(sources, st.session_state.column_changes + [change])
    except ValueError as exc:
        st.error(str(exc))
        return
    st.session_state.column_changes.append(change)
    st.session_state.edit_revision += 1
    st.rerun()


with st.sidebar:
    st.markdown('''<div class="sidebar-brand" aria-label="DataMerge Studio">
    <span class="merge-icon" aria-hidden="true">
    <svg width="32" height="28" viewBox="0 0 32 28" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3 14H11M7 9L12 14L7 19" stroke="#E7FFF3" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M29 14H21M25 9L20 14L25 19" stroke="#A3E7C7" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="14.5" y="7" width="3" height="14" rx="1.5" fill="white"/>
    </svg></span>
    <div><div class="brand-name">DataMerge</div><div class="brand-subtitle">Studio</div></div>
    </div>''', unsafe_allow_html=True)
    section = st.radio('Workspace', ['Upload', 'Data Mapping', 'Export'], key='workspace_page')

st.title('DataMerge Studio')
st.caption('Upload spreadsheets. Preview the combined output. Download your file.')
if section != 'Upload':
    previous = 'Upload' if section == 'Data Mapping' else 'Data Mapping'
    st.button(f'← Back to {previous}', on_click=navigate, args=(previous,))

if section == 'Upload':
    st.header('Upload files')
    st.button('Clear data', on_click=clear_data, help='Remove uploaded files, worksheet selections, and column changes from this session.')
    uploads = st.file_uploader('Choose CSV or Excel files', type=['csv', 'xlsx'], accept_multiple_files=True, key=upload_key)
    st.session_state.selected_inputs = [(f.name, f.getvalue()) for f in uploads]
    st.caption('Up to 10 files. Excel worksheets are included by default; expand a workbook below to choose sheets. Use non-confidential data.')
    for name, content in st.session_state.selected_inputs:
        if name.lower().endswith('.xlsx'):
            identity = hashlib.sha256(name.encode() + content).hexdigest()
            try:
                available = worksheets(content)
                if len(available) > 1:
                    with st.expander(f'Worksheets · {name}', expanded=False):
                        selected = st.multiselect('Worksheets to include', available,
                            default=st.session_state.sheet_choices.get(identity, available), key=f'sheets-{identity}')
                else:
                    selected = available
                st.session_state.sheet_choices[identity] = selected
            except Exception:
                pass  # Shared inspection below reports file-specific failures.
else:
    if upload_key in st.session_state:
        st.session_state[upload_key] = st.session_state[upload_key]

inputs = st.session_state.selected_inputs
if not inputs:
    st.info('Add files on the Upload page to begin.')
    st.stop()

try:
    selection = {name: st.session_state.sheet_choices.get(hashlib.sha256(name.encode() + content).hexdigest())
                 for name, content in inputs if name.lower().endswith('.xlsx')}
    selection = {name: value for name, value in selection.items() if value is not None}
    sources, errors = inspect_uploads(inputs, selection)
except Exception as exc:
    st.error(str(exc))
    st.stop()
for error in errors:
    st.error(error)
if errors:
    st.info('Correct or remove the affected files on Upload. Export is blocked so no dataset is silently omitted.')
    st.stop()
try:
    signature = hashlib.sha256(json.dumps(selection, sort_keys=True).encode() +
                               b''.join(name.encode() + hashlib.sha256(content).digest() for name, content in inputs)).hexdigest()
    if st.session_state.get('input_signature') != signature:
        had_changes = bool(st.session_state.column_changes)
        st.session_state.column_changes = []
        st.session_state.edit_revision += 1
        st.session_state.input_signature = signature
        if had_changes:
            st.info('Inputs changed. Previous column edits were cleared so you can review the new data.')
    master = prepare_output(sources, st.session_state.column_changes)
except Exception as exc:
    st.error(f'Cannot prepare the output: {exc}')
    st.stop()

input_rows = sum(len(source.frame) for source in sources)
st.caption(f'{len(inputs)} files · {len(sources)} datasets · {input_rows:,} input rows → {len(master):,} output rows. No rows removed.')
if section == 'Upload':
    st.button('Next: Review data →', type='primary', on_click=navigate, args=('Data Mapping',))
elif section == 'Data Mapping':
    st.header('File previews')
    st.caption('Expand a file to view its first 10 records. Excel worksheets have separate previews.')
    for name, _ in inputs:
        with st.expander(name, expanded=False):
            for source in sources:
                if source.name != name:
                    continue
                if source.sheet:
                    with st.expander(source.sheet, expanded=False):
                        st.caption(f'{len(source.frame):,} records | {len(source.frame.columns)} columns')
                        st.dataframe(source.frame.head(10), hide_index=True, use_container_width=True)
                else:
                    st.caption(f'{len(source.frame):,} records | {len(source.frame.columns)} columns')
                    st.dataframe(source.frame.head(10), hide_index=True, use_container_width=True)
    st.divider()
    st.header('Review columns')
    partial = [column for column in dict.fromkeys(c for source in sources for c in source.frame.columns)
               if sum(column in source.frame.columns for source in sources) < len(sources)]
    if partial:
        st.caption('Columns found in only some datasets: ' + ', '.join(partial) + '. Missing values remain blank unless you match columns below.')
    with st.expander('Match or drop columns', expanded=False):
        st.caption('Optional: match names for the same information, or drop unwanted output columns. Original files stay unchanged.')
        revision = st.session_state.edit_revision
        columns = list(master.columns)
        matched = st.multiselect('Columns that mean the same thing', columns, key=f'match-{revision}')
        target = st.selectbox('Keep this column name', matched, index=0 if matched else None, disabled=not matched,
                              key=f'target-{revision}-{json.dumps(matched)}')
        if st.button('Treat as the same column', disabled=len(matched) < 2):
            save_change({'kind': 'merge', 'columns': matched, 'name': target}, sources)
        dropped = st.multiselect('Columns to drop', columns, key=f'drop-{revision}')
        if st.button('Drop column', disabled=not dropped):
            save_change({'kind': 'drop', 'columns': dropped}, sources)
    if st.session_state.column_changes:
        st.caption('Applied changes: ' + '; '.join(
            ('Matched ' + ', '.join(c['columns']) + ' as ' + c['name']) if c['kind'] == 'merge'
            else ('Dropped ' + ', '.join(c['columns'])) for c in st.session_state.column_changes))
        if st.button('Undo last change'):
            st.session_state.column_changes.pop()
            st.session_state.edit_revision += 1
            st.rerun()
    st.header('Output preview')
    st.caption('First 10 output records, including your column changes. Identical names share a column; other names stay separate unless you match them. Missing fields are blank. Source order and duplicate records are retained.')
    st.dataframe(master.head(10), hide_index=True, use_container_width=True)
    st.caption(f'{len(master):,} output records · {len(master.columns)} columns')
    st.button('Next: Export →', type='primary', on_click=navigate, args=('Export',))
else:
    st.header('Export')
    st.caption(f'{len(master):,} records · {len(master.columns)} columns. Column order follows first appearance across the uploaded datasets.')
    output_type = st.selectbox('Output file type', ['Excel (.xlsx)', 'CSV (.csv)'])
    try:
        if output_type == 'Excel (.xlsx)':
            st.download_button('Download Excel', master_excel_bytes(master), 'datamerge-master.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else:
            st.download_button('Download CSV', master.to_csv(index=False), 'datamerge-master.csv', 'text/csv')
            st.caption('CSV preserves raw text; spreadsheet applications may interpret formula-like values. Excel output stores such values as text.')
    except Exception as exc:
        st.error(f'Cannot create the export: {exc}')
