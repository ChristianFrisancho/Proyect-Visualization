import os, io
from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'Energy_clean.csv')

_CACHE = {"mtime": None, "df": None, "year_cols": None, "years": None}

def _load_df_cached():
    mtime = os.path.getmtime(DATA_PATH)
    if _CACHE["df"] is None or _CACHE["mtime"] != mtime:
        df = pd.read_csv(DATA_PATH)
        year_cols = [c for c in df.columns if c.startswith('F')]
        df[year_cols] = df[year_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)
        for col in ["Country","ISO3","Energy_Type","Technology"]:
            if col in df.columns:
                df[col] = df[col].astype(str)
        years = sorted(int(c[1:]) for c in year_cols if c[1:].isdigit())
        _CACHE.update({"mtime": mtime, "df": df, "year_cols": year_cols, "years": years})
    return _CACHE["df"], _CACHE["year_cols"], _CACHE["years"]

def _parse_year_param(raw):
    if not raw: return None
    _, year_cols, _ = _load_df_cached()
    s = str(raw).strip()
    if s.startswith('F'):  return s if s in year_cols else None
    if s.isdigit():        return f'F{s}' if f'F{s}' in year_cols else None
    return None

def _attach_energy_value(df, year_col):
    df = df.copy()
    if year_col:
        df["Energy_Value"] = df[year_col].astype(float)
    else:
        _, year_cols, _ = _load_df_cached()
        df["Energy_Value"] = df[year_cols].sum(axis=1).astype(float)
    return df

def _apply_filters(df, energy_type=None, technology=None, isos=None):
    if energy_type:
        df = df[df["Energy_Type"].str.contains(energy_type, case=False, na=False)]
    if technology:
        df = df[df["Technology"].str.contains(technology, case=False, na=False)]
    if isos:
        iso_set = {s.strip().upper() for s in isos if s and s.strip()}
        if iso_set:
            df = df[df["ISO3"].str.upper().isin(iso_set)]
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/years')
def api_years():
    _, _, years = _load_df_cached()
    return jsonify({"years": years})

@app.route('/api/data')
def api_data():
    df, _, _ = _load_df_cached()
    year = _parse_year_param(request.args.get('year'))
    energy_type = request.args.get('energy_type')
    technology = request.args.get('technology')
    df = _apply_filters(df, energy_type=energy_type, technology=technology)
    df = _attach_energy_value(df, year)
    if df.empty: return jsonify([])
    grouped = (df.groupby(['Country','ISO3','Energy_Type','Technology'], as_index=False)
                 ['Energy_Value'].sum())
    grouped['Energy_Value'] = grouped['Energy_Value'].astype(float)
    return jsonify(grouped.to_dict(orient='records'))

@app.route('/api/aggregated')
def api_aggregated():
    df, _, _ = _load_df_cached()
    year = _parse_year_param(request.args.get('year'))
    isos_param = request.args.get('isos')
    isos = [s for s in isos_param.split(',')] if isos_param else None

    df = _apply_filters(df, isos=isos)
    df = _attach_energy_value(df, year)
    if df.empty:
        return jsonify({"total": 0.0, "breakdown": [], "tech_breakdown": [], "pairs": []})

    total = float(df['Energy_Value'].sum())

    br = (df.groupby('Energy_Type', as_index=False)['Energy_Value'].sum())
    br['pct'] = (br['Energy_Value'] / (total if total>0 else 1) * 100).round(2)
    br = br.sort_values('Energy_Value', ascending=False).reset_index(drop=True)

    tech = (df.groupby('Technology', as_index=False)['Energy_Value'].sum())
    tech['pct'] = (tech['Energy_Value'] / (total if total>0 else 1) * 100).round(2)
    tech = tech.sort_values('Energy_Value', ascending=False).reset_index(drop=True)

    # NUEVO: pares Energy_Type x Technology para construir el sunburst RN -> tecnologías
    pairs = (df.groupby(['Energy_Type','Technology'], as_index=False)['Energy_Value'].sum())
    pairs['pct'] = (pairs['Energy_Value'] / (total if total>0 else 1) * 100).round(2)
    pairs = pairs.sort_values('Energy_Value', ascending=False).reset_index(drop=True)

    return jsonify({
        "total": total,
        "breakdown": br.to_dict(orient='records'),
        "tech_breakdown": tech.to_dict(orient='records'),
        "pairs": pairs.to_dict(orient='records')
    })

@app.route('/api/country_details')
def api_country_details():
    df, _, _ = _load_df_cached()
    iso = request.args.get('iso')
    year = _parse_year_param(request.args.get('year'))
    if not iso: return jsonify({'error': 'iso required'}), 400
    dfc = df[df['ISO3'].str.upper() == iso.upper()].copy()
    if dfc.empty: return jsonify([])
    dfc = _attach_energy_value(dfc, year)
    return jsonify(dfc.to_dict(orient='records'))

@app.route('/api/download_country_csv')
def api_download_country_csv():
    df, _, _ = _load_df_cached()
    iso = request.args.get('iso')
    if not iso: return jsonify({'error':'iso required'}), 400
    dfc = df[df['ISO3'].str.upper() == iso.upper()]
    if dfc.empty: return jsonify({'error':'no data'}), 404
    mem = io.StringIO()
    dfc.to_csv(mem, index=False)
    mem.seek(0)
    return send_file(io.BytesIO(mem.getvalue().encode('utf-8')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f'{iso}_data.csv')

if __name__ == '__main__':
    app.run(debug=True)
