import pandas as pd
import json
import os

base = r'E:\bob-ai-hackathon-KMStra\src'
output_dir = rf'{base}\frontend\src\data'
os.makedirs(output_dir, exist_ok=True)

assets = pd.read_csv(rf'{base}\data\ingestion\synthetic\assets.csv')
missions = pd.read_csv(rf'{base}\data\ingestion\synthetic\missions.csv')
health = pd.read_csv(rf'{base}\models\health\health_scores.csv')
failure = pd.read_csv(rf'{base}\models\failure\failure_scores.csv')
rul = pd.read_csv(rf'{base}\models\rul\rul_predictions.csv')

health = health.groupby('unit').last().reset_index()
failure = failure.groupby('unit').last().reset_index()
rul = rul.groupby('asset_id').last().reset_index()

assets['asset_id'] = assets['asset_id'].astype(str)
rul['asset_id'] = rul['asset_id'].astype(str)

health['asset_id'] = health['unit'].apply(lambda x: f'ENG-{int(x):03d}')
failure['asset_id'] = failure['unit'].apply(lambda x: f'ENG-{int(x):03d}')

df = assets.merge(health[['asset_id', 'health_score', 'anomaly_score']], on='asset_id', how='left')
df = df.merge(failure[['asset_id', 'failure_probability']], on='asset_id', how='left')
df = df.merge(rul[['asset_id', 'predicted_rul']], on='asset_id', how='left')

missions['asset_id'] = missions['asset_id'].astype(str)
missions['mission_date'] = pd.to_datetime(missions['mission_date'])
next_missions = missions.sort_values('mission_date').groupby('asset_id').first().reset_index()
next_missions['mission_date'] = next_missions['mission_date'].dt.strftime('%Y-%m-%d')
df = df.merge(next_missions[['asset_id', 'mission_type', 'mission_criticality', 'mission_date']], on='asset_id', how='left')
df = df.fillna(-1)

df.to_json(rf'{output_dir}\actualData.json', orient='records')

# Timeseries
health_ts = pd.read_csv(rf'{base}\models\health\health_scores.csv')
failure_ts = pd.read_csv(rf'{base}\models\failure\failure_scores.csv')
rul_ts = pd.read_csv(rf'{base}\models\rul\rul_predictions.csv')

health_ts['asset_id'] = health_ts['unit'].apply(lambda x: f'ENG-{int(x):03d}')
failure_ts['asset_id'] = failure_ts['unit'].apply(lambda x: f'ENG-{int(x):03d}')
rul_ts['asset_id'] = rul_ts['asset_id'].astype(str)

ts = health_ts[['asset_id', 'cycle', 'health_score']].merge(failure_ts[['asset_id', 'cycle', 'failure_probability']], on=['asset_id', 'cycle'], how='outer')
ts = ts.merge(rul_ts[['asset_id', 'cycle', 'predicted_rul']], on=['asset_id', 'cycle'], how='outer')
ts = ts.sort_values(['asset_id', 'cycle']).fillna(-1)

ts_dict = {k: v.to_dict(orient='records') for k, v in ts.groupby('asset_id')}
with open(rf'{output_dir}\timeSeriesData.json', 'w') as f:
    json.dump(ts_dict, f)

print('Data generation complete.')
