from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
import os, io

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'Energy_clean.csv')

def load_df():
    df = pd.read_csv(DATA_PATH)
    year_cols = [c for c in df.columns if c.startswith('F')]
    df[year_cols] = df[year_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    return df, year_cols

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/years')
def api_years():
    df, years = load_df()
    return jsonify({'years': [int(y[1:]) for y in years]})

@app.route('/api/data')
def api_data():
    df, year_cols = load_df()
    year = request.args.get('year', 'Total')
    tech = request.args.get('technology', None)

    if tech:
        df = df[df['Technology'].astype(str).str.contains(tech, case=False, na=False)]

    if year == 'Total':
        df['Energy_Value'] = df[year_cols].sum(axis=1)
    else:
        if year not in year_cols:
            return jsonify([])
        df['Energy_Value'] = df[year].astype(float)

    grouped = df.groupby(['Country','ISO3'], as_index=False)['Energy_Value'].sum()
    grouped['Energy_Value'] = grouped['Energy_Value'].astype(float)
    grouped['count_rows'] = df.groupby(['Country','ISO3']).size().reindex(grouped.set_index(['Country','ISO3']).index).values
    return jsonify(grouped.to_dict(orient='records'))

@app.route('/api/hierarchy')
def api_hierarchy():
    df, year_cols = load_df()
    year = request.args.get('year', 'Total')
    country = request.args.get('country', None)
    tech_filter = request.args.get('tech_filter', None)

    if country:
        df = df[df['ISO3'].astype(str).str.upper() == country.upper()]
    if tech_filter:
        df = df[df['Technology'].astype(str).str.contains(tech_filter, case=False, na=False)]

    if year == 'Total':
        df['Energy_Value'] = df[year_cols].sum(axis=1)
    else:
        if year not in year_cols:
            return jsonify([])
        df['Energy_Value'] = df[year].astype(float)

    agg = df.groupby(['Energy_Type','Technology'], as_index=False)['Energy_Value'].sum()
    agg['Energy_Value'] = agg['Energy_Value'].astype(float)
    return jsonify(agg.to_dict(orient='records'))

@app.route('/api/countries_breakdown')
def api_countries_breakdown():
    df, year_cols = load_df()
    isos = request.args.get('isos')
    year = request.args.get('year', 'Total')
    if not isos:
        return jsonify({'error':'isos required'}), 400
    iso_list = [s.strip().upper() for s in isos.split(',') if s.strip()]

    df_sel = df[df['ISO3'].astype(str).str.upper().isin(iso_list)]
    if df_sel.empty:
        return jsonify({'isos': iso_list, 'total': 0, 'breakdown': [], 'tech_breakdown': [], 'rows_count': 0})

    if year == 'Total':
        df_sel['Energy_Value'] = df_sel[year_cols].sum(axis=1)
    else:
        if year not in year_cols:
            return jsonify({'error':'invalid year'}), 400
        df_sel['Energy_Value'] = df_sel[year].astype(float)

    total = float(df_sel['Energy_Value'].sum())
    br = df_sel.groupby('Energy_Type', as_index=False)['Energy_Value'].sum()
    br['pct'] = (br['Energy_Value'] / total * 100).round(2).fillna(0)
    br = br.sort_values('Energy_Value', ascending=False)
    tech = df_sel.groupby('Technology', as_index=False)['Energy_Value'].sum().sort_values('Energy_Value', ascending=False)
    tech['pct'] = (tech['Energy_Value'] / total * 100).round(2).fillna(0)

    return jsonify({
        'isos': iso_list,
        'year': year,
        'total': total,
        'breakdown': br.to_dict(orient='records'),
        'tech_breakdown': tech.to_dict(orient='records'),
        'rows_count': int(len(df_sel))
    })

@app.route('/api/country_details')
def api_country_details():
    df, year_cols = load_df()
    iso = request.args.get('iso')
    year = request.args.get('year', 'Total')
    tech = request.args.get('technology', None)
    if not iso:
        return jsonify({'error':'iso required'}), 400

    df_country = df[df['ISO3'].astype(str).str.upper() == iso.upper()]
    if tech:
        df_country = df_country[df_country['Technology'].astype(str).str.contains(tech, case=False, na=False)]

    if year == 'Total':
        df_country['Energy_Value'] = df_country[year_cols].sum(axis=1)
    else:
        if year not in year_cols:
            return jsonify([])
        df_country['Energy_Value'] = df_country[year].astype(float)

    df_country = df_country.fillna('').astype(object)
    rows = df_country.to_dict(orient='records')
    return jsonify(rows)

@app.route('/api/download_country_csv')
def api_download_country_csv():
    df, year_cols = load_df()
    iso = request.args.get('iso')
    if not iso:
        return jsonify({'error':'iso required'}), 400
    df_country = df[df['ISO3'].astype(str).str.upper() == iso.upper()]
    if df_country.empty:
        return jsonify({'error':'no data'}), 404
    mem = io.StringIO()
    df_country.to_csv(mem, index=False)
    mem.seek(0)
    return send_file(io.BytesIO(mem.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, attachment_filename=f'{iso}_data.csv')

if __name__ == '__main__':
    app.run(debug=True)
