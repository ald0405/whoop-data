import pandas as pd 
import numpy 
import seaborn as sns 
import matplotlib.pyplot as plt
df = pd.read_csv("Data/recovery_data.csv")

df.info()



df['day_of_week'] =pd.to_datetime(df['created_ts']).dt.day_of_week

df['is_weekend'] = df['day_of_week'] > 4


sns.scatterplot(x = 'total_sleep_time_hrs', y = 'recovery_score',data = df, hue = 'is_weekend')
plt.show()

(df.groupby(['is_weekend'])['total_sleep_time_hrs']
    .mean()
    .reset_index()
    .to_dict(orient="tight")
    )

sns.histplot(x = 'recovery_score', data = df, hue='is_weekend',kde=True)
plt.show()
 