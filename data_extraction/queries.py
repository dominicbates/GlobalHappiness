import pandas as pd
import time
import json
from openai import OpenAI
import io
import numpy as np


def query_model(client, prompt: str):
    '''
    Query model and extract text
    '''
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    reply = response.choices[0].message.content

    return reply




def build_prompt(region: str, extra: str = '') -> str:
    '''
    Prompt to extract csv for a specific region
    '''
    return f"""
You are a historical data analyst who is an expert on {region}{extra}.

For this region, you will be estimating how several different quality of life factors vary across time.

Years you will provide data for: -1000 to 2025 in intervals of 100 years (-1000 to -900, -900 to -800, ..., 2000 to 2025)

For each period, please provide:
- A short one-sentence summary of what is happening in {region}
- The rough population of the region in this period (as a number, e.g. 2,300,000)
- A numeric score from 0 to 10 for each category based on the life of the average person in {region} over this period (0 being worst, 10 being best)

Return the data as a **CSV table** with the following columns (headers must be included):

Start Year,End Year,Population,Summary,Freedom,Health & Wellbeing,Economic Opportunity,Equality,Culture & Lesure,Peace

Some additional context on what each category represents:
- Freedom (e.g. freedom of speech, movement, ideas, democracy, slavery etc.)
- Health & Wellbeing (e.g. mortality, disease, access to food, cleanliness)
- Economic Opportunity (e.g. availability of jobs, education, economic prosperity, social mobility)
- Equality (e.g. disparity between rich and poor)
- Culture & Lesure (e.g. access to games, hobbies, cuisine, free time, and cultural expression)
- Peace (e.g. wars, invasions, unrest, or infighting) - where 10 is most peaceful

Only return the CSV table, no markdown, no JSON, no intro or outro text. Please encode / surround ALL values with quotation marks " and remember this is just for {region}
"""




def query_region(client, region: str, extra: str = '', debug=False):
    '''
    Query model and extract data for this region
    '''
    prompt = build_prompt(region, extra=extra)

    reply = query_model(client, prompt)

    if debug==True:
        print(prompt)
    try:
        df = pd.read_csv(io.StringIO(reply.replace('""','"')))
        df["region"] = region
        return df, reply
    except Exception as e:
        print("❌ Failed to parse CSV")
        print(reply)
        return None, reply




def query_region_n_times(client, region: str, extra: str = '', n_repeats=1, debug=False):
    '''
    Runs the query many times and returns a list of outputs
    '''
    print('Querying for region:',region)
    list_df = []
    list_reply = []
    for n in range(n_repeats):
        print(n+1,'/',n_repeats)
        df, reply = query_region(client, region, extra=extra, debug=debug)
        list_df.append(df)
        list_reply.append(reply)
        
    return list_df, list_reply






def process_dfs(list_df, region):
    '''
    Slightly messy function which firsly checks input format (probably should be a 
    seperate function), then combined all extracted values in to a single stacked csv
    '''
    # List of columns
    cols = ['Freedom','Health & Wellbeing','Economic Opportunity','Equality','Culture & Lesure','Peace']

    # Expected number of rows
    list_df = [df for df in list_df if df is not None]
    expected_rows = int(np.median([len(df) for df in list_df]))
    
    # Check all inputs
    new_dfs = []
    for n, df in enumerate(list_df):
        success = 1

        try:
            assert len(df) == expected_rows # Wrong length
        except:
            print(str(n)+': Wrong number of rows'); success = 0
        try:
            df['Overall'] = df[cols].mean(axis=1) # Avergae to get overall
        except:
            print(str(n)+': Failed to average all values to get overall'); success = 0
        try:
            df['Start Year'] = df['Start Year'].astype(int)
            df['End Year'] = df['End Year'].astype(int)
        except:
            print(str(n)+': Failed to extract dates'); success = 0
        try:
            df['Population'] = df['Population'].astype(str).str.replace(',','').replace('~','').astype(int)
        except:
            print(str(n)+': Failed to extract population'); success = 0

        if success == 1:
            new_dfs.append(df)
        else:
            print('Ignoring',n,'due to above errors')
    list_df = new_dfs 

    # Loop through all features
    dfs = []
    for col in cols + ['Overall', 'Population']:

        # Avergae over all LLM outputs
        list_vals = []
        list_dates_start = []
        list_dates_end = []
        list_summaries = []
        for df in list_df:
            list_vals.append(df[col].values)
            list_dates_start.append(df['Start Year'].values)
            list_dates_end.append(df['End Year'].values)
            list_summaries.append(list(df['Summary'].values))

        # Make arrays for np operations
        vals = np.array(list_vals)
        dates_start = np.array(list_dates_start)
        dates_end = np.array(list_dates_end)

        # Add to dataframe
        df_metric = pd.DataFrame()
        df_metric['dates_start'] = np.median(dates_start, axis=0)
        df_metric['dates_end'] = np.median(dates_end, axis=0)
        df_metric['mean'] = np.mean(vals,axis=0)
        df_metric['err_pos'] = np.percentile(vals,axis=0,q=84)
        df_metric['err_neg'] = np.percentile(vals,axis=0,q=16)
        df_metric['sd_pos'] = df_metric['mean'] + np.std(vals,axis=0)
        df_metric['sd_neg'] = df_metric['mean'] - np.std(vals,axis=0)
        df_metric['region'] = region
        df_metric['metric'] = col
        dfs.append(df_metric)

    return pd.concat(dfs), list_summaries




def clean_dates(date_1, date_2):
    '''
    Returns human-readable date range (CE, BCE...)
    '''
    clean = ''
    if test<0:
        clean = str(date_1).replace('-','') +' to '+str(date_2).replace('-','') +' BCE'
    else:
        clean = str(date_1).replace('-','') +' to '+str(date_2).replace('-','') +' CE'
    return clean
    