import pandas as pd

df = pd.read_csv("data/welfare_20241231.csv", encoding="cp949")


df2024 = df[df["기준년월"]=="Dec-24"]

print(df2024.head())