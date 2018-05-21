import peakutils
import pandas as pd
import numpy as np

from wizardtracker.models import DB, Race, RaceReceiver, RaceRssi


def get_times(race_id):
    receivers = RaceReceiver \
        .select() \
        .where(RaceReceiver.race == race_id) \
        .prefetch(RaceRssi)

    for receiver in receivers:
        df_data = {
            'timestamp': [],
            'rssi': []
        }

        for rssi in receiver.rssi:
            df_data['timestamp'].append(rssi.timestamp)
            df_data['rssi'].append(rssi.value)

        df = pd.DataFrame(data=df_data)
        max_timestamp = df['timestamp'].max()
        df['timestamp'] = max_timestamp - df['timestamp']
        df['rssi'] = df['rssi'] / 255.0
        df['rssi_delta'] = -np.gradient(df['rssi'])

        baseline = peakutils.baseline(df['rssi'], 2)
        df['rssi'] = df['rssi'] - baseline

        peak_indices = peakutils.indexes(df['rssi'], thres=0.5, min_dist=30)
        peak_indices = list(reversed(peak_indices))

        for i, peak_index in enumerate(peak_indices):
            df_row = df.iloc[peak_index]

            if i == 0:
                lap_time = df_row['timestamp']
            else:
                df_row_last = df.iloc[peak_indices[i - 1]]
                lap_time = df_row['timestamp'] - df_row_last['timestamp']

            print('{} - {}s'.format(receiver.id, lap_time))

        print('')
