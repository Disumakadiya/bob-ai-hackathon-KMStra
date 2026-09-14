import pandas as pd
import json
import os

base = r'E:\bob-ai-hackathon-KMStra\src'
output_dir = rf'{base}\frontend\src\data'

health_ts = pd.read_csv(rf'{base}\models\health\health_scores.csv')
failure_ts = pd.read_csv(rf'{base}\models\failure\failure_scores.csv')
rul_ts = pd.read_csv(rf'{base}\models\rul\rul_predictions.csv')

health_ts['asset_id'] = health_ts['unit'].apply(lambda x: f'ENG-{int(x):03d}')
failure_ts['asset_id'] = failure_ts['unit'].apply(lambda x: f'ENG-{int(x):03d}')
rul_ts['asset_id'] = rul_ts['asset_id'].astype(str).str.replace('ENG-', '', regex=False).astype(float).astype(int).apply(lambda x: f'ENG-{x:03d}')

ts = health_ts[['asset_id', 'cycle', 'health_score']].merge(failure_ts[['asset_id', 'cycle', 'failure_probability']], on=['asset_id', 'cycle'], how='outer')
ts = ts.merge(rul_ts[['asset_id', 'cycle', 'predicted_rul']], on=['asset_id', 'cycle'], how='outer')
ts = ts.sort_values(['asset_id', 'cycle']).fillna(-1)

ts_dict = {k: v.to_dict(orient='records') for k, v in ts.groupby('asset_id')}
with open(rf'{output_dir}\timeSeriesData.json', 'w') as f:
    json.dump(ts_dict, f)

print('Timeseries regenerated.')
