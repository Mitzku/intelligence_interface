from serpapi import GoogleSearch
import pandas as pd
import re

def process_search(search, df=None):
    date = search.get_dict()['search_metadata']['created_at']
    query = search.get_dict()['search_parameters']['q']
    engine = search.get_dict()['search_parameters']['engine']

    # Initialize the DataFrame if not provided
    if df is None:
        data = {'date': [date], 'query': [query], 'engine': [engine]}
        df = pd.DataFrame(data)

    # Retrieve information on the links
    organic_results = search.get_dict()['organic_results']
    position = pd.DataFrame({'position': [entry['position'] for entry in organic_results]})
    title = pd.DataFrame({'title': [entry['title'] for entry in organic_results]})
    link = pd.DataFrame({'link': [entry['link'] for entry in organic_results]})
    date = pd.DataFrame({'date': [entry['date'] if 'date' in entry else None for entry in organic_results]})
    source = pd.DataFrame({'source': [entry['source'] for entry in organic_results]})

    # Merge the DataFrames
    df = pd.concat([df, position, title, link, date, source], axis=1)
    df['date'] = df['date'].ffill()
    df['query'] = df['query'].ffill()
    df['engine'] = df['engine'].ffill()

    return df

def perform_google_search(query_list, params, max_results):
    all_results = []  # Initialize an empty list to hold all DataFrames
    
    for query in query_list:
        query_results = []  # Initialize an empty list to hold individual query results
        start_value = 0  # Initial start value
        
        while len(query_results) < max_results:
            try:
                # Update the query in params
                params["q"] = query
                
                # Update the start value in params
                params["start"] = start_value
                
                # Perform the search
                search = GoogleSearch(params)
                json_response = search.get_dict()
                
                # Extract next page link
                next_link = json_response.get('serpapi_pagination', {}).get('next_link')
                if not next_link:
                    break  # No more pages, break out of the loop
                
                match = re.search(r'start=(\d+)', next_link)
                if match:
                    start_value = int(match.group(1))
                else:
                    break  # No more pages, break out of the loop

                # Process the search results
                temp_df = process_search(search)
                query_results.append(temp_df)
            except Exception as e:
                print(f"Error in performing search for query '{query}': {e}")
                break  # Break out of the loop on error
        
        # Append the list of DataFrames for this query to all_results
        all_results.append(query_results)
    
    return all_results
