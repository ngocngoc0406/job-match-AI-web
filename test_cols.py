import pandas as pd
df = pd.read_excel('db_job_tuan.xlsx')
for col in df.columns:
    print(col)
