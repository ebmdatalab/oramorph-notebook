# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: all
#     notebook_metadata_filter: all,-language_info
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# ## Assessing trends in prescribing of oral morphine 10mg/5ml oral solution .....better know as _Oramorph_
#
# This notebook seeks to 
# 1. [Assess the trends at a national level over time](#national)
# 2. [Variation by CCGs](#ccgs) 
# 3. [Varination and Excessive quntitites](#excessive)
# 3. Insert here............

##importing libraries that are need to support analysis
import pandas as pd
import numpy as np
import plotly.express as px
from ebmdatalab import bq, maps, charts
import matplotlib.pyplot as plt
import os

#this sets £ and pence appropriately
pd.set_option('display.float_format', lambda x: '%.2f' % x)

# +
sql = '''
SELECT
  pct,
  month,
  bnf_name,
  bnf_code,
  quantity_per_item,
  SUM(items) AS total_items,
  SUM(actual_cost) AS total_cost
FROM
  ebmdatalab.hscic.raw_prescribing_normalised AS rx
INNER JOIN
  hscic.ccgs
ON
  rx.pct = ccgs.code
WHERE
  org_type = 'CCG'
  AND bnf_code LIKE '0407020Q0%CN'
GROUP BY
  pct,
  month,
  bnf_code,
  bnf_name,
  quantity_per_item
ORDER BY
  pct,
  month,
  bnf_code'''

df_oramorph_ccg = bq.cached_read(sql, csv_path=os.path.join('..','data','oramorph_ccg.csv'))

# -

df_oramorph_ccg['month'] = df_oramorph_ccg['month'].astype('datetime64[ns]')

df_oramorph_ccg["bnf_name"].unique()

df_oramorph_ccg["bnf_code"].unique()

df_oramorph_ccg.head(10)

# +
## here we add a qty X items column
df_total_oramorph_ccg= df_oramorph_ccg.copy()

df_total_oramorph_ccg["quantity_times_item"] = df_oramorph_ccg.quantity_per_item * df_oramorph_ccg.total_items
df_total_oramorph_ccg.head()
# -

# # National Level Over Time <a id='national'></a>

#items
df_total_oramorph_ccg.groupby("month")['total_items'].sum().plot(kind='line', title="Total number items of Oramorph")
plt.ylim(0, 250000)

#total nmer of ml
df_total_oramorph_ccg.groupby("month")['quantity_times_item'].sum().plot(kind='line', title="Total number milliliters of Oramorph")
plt.ylim(0,60000000)

#total cost
df_total_oramorph_ccg.groupby("month")['total_cost'].sum().plot(kind='line', title="Total cost [£] of Oramorph")
plt.ylim(0, 1200000)

# # Variation in quantity on each prescription plus identify excessive quantities <a id='excessive'></a>

# +
## Oty per scrpit
# -

df_2019_oramorph_ccg = df_total_oramorph_ccg.loc[(df_total_oramorph_ccg["month"] >= '2019-01-01') & (df_total_oramorph_ccg["month"] <= '2019-12-01')] #restict to 2019
df_2019_oramorph_ccg = df_2019_oramorph_ccg.groupby(["quantity_per_item"]).sum().reset_index()
df_2019_oramorph_ccg["quantity_times_item"] = df_2019_oramorph_ccg.quantity_per_item * df_2019_oramorph_ccg.total_items
df_2019_oramorph_ccg .head(5)

df_2019_oramorph_ccg.plot(x= "quantity_per_item", y="total_items", kind='hist')

####  Using plotly to give zoom capabilites ZOOM IN BELOW
fig = px.bar(df_2019_oramorph_ccg, x='quantity_per_item', y='total_items')
fig.show()

Excess_qty_2019 = df_2019_oramorph_ccg.sort_values(by = "quantity_per_item", ascending= False).reset_index()
Excess_qty_2019.head(6)

# Jon Hayhurst & Robin Conibere have [indicated on Twitter that 6L](https://twitter.com/Jon_SWestNHS/status/1293293708545265675) is an excessve amount of Oramorph on a single prescription so this show that in 2019, 66 items were remibursed where the quantity was 6L or more.

# # CCG Variation <a id='ccgs'></a>

df_total_oramorph_ccg.head()

ccg_measure_qty = df_total_oramorph_ccg.groupby(["pct","month"])["quantity_times_item"].sum().reset_index()
ccg_measure_qty.head(5)

# +
#ccg_measure_qty.info()
#ccg_measure_qty['month'] = ccg_measure_qty['month'].astype('datetime64[ns]')

# +
sql2 = """
SELECT month, 
pct_id AS pct,
AVG(total_list_size) AS list_size
FROM ebmdatalab.hscic.practice_statistics
group by 
month, pct
order by
month, pct,
list_size
"""
df_list = bq.cached_read(sql2, csv_path=os.path.join('..','data', 'listsize_ccg.csv'))
df_list['month'] = df_list['month'].astype('datetime64[ns]')
df_list.head(5)


# -

ccg_oramorph_measure = pd.merge(ccg_measure_qty, df_list, on=['month', 'pct'])
ccg_oramorph_measure["ml_per_1000_pts"] = 1000* (ccg_oramorph_measure['quantity_times_item']/ccg_oramorph_measure['list_size'])
ccg_oramorph_measure.head(5)

# +
#create sample deciles & prototype measure
charts.deciles_chart(
        ccg_oramorph_measure,
        period_column='month',
        column='ml_per_1000_pts',
        title="Millilitres of Oramorph per 1000 patients \n CCG deciles",
        show_outer_percentiles=False)

#add in example CCG (Devon)
df_subject = ccg_oramorph_measure.loc[ccg_oramorph_measure['pct'] == '15N']
plt.plot(df_subject['month'], df_subject['ml_per_1000_pts'], 'r--')

plt.show()
# -

#create choropeth map of cost per 1000 patients
plt.figure(figsize=(12, 7))
latest_ccg_oramorph_measure= ccg_oramorph_measure.loc[(ccg_oramorph_measure['month'] >= '2019-01-01') & (ccg_oramorph_measure['month'] <= '2019-12-01')]
#latest_ccg_oramorph_measure= ccg_oramorph_measure.loc[(ccg_oramorph_measure['month'] >= '2020-04-01') & (ccg_oramorph_measure['month'] <= '2020-06-01')]
plt = maps.ccg_map(latest_ccg_oramorph_measure, title="Millilitres of Oramorph per 1000 patients \n England 2019 ", column='ml_per_1000_pts', separate_london=True)
plt.show()


