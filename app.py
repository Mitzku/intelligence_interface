from flask import Flask, request, render_template
import pandas as pd
from serpapi import GoogleSearch
import re
from datetime import datetime
import time
import uuid

app = Flask(__name__)

# API key for SerpAPI
API_KEY = "5a62bf2d11d72e0672c9000fcf9dd0ec9113237e4e334889df56acdabdb640ed"

# Function to process Naver web search results
def process_naver_web_search(search, df=None):
    date = search.get_dict()['search_metadata']['created_at']
    query = search.get_dict()['search_parameters']['query']
    engine = search.get_dict()['search_parameters']['engine']

    if df is None:
        data = {'date': [date], 'query': [query], 'engine': [engine]}
        df = pd.DataFrame(data)
    
    organic_results = search.get_dict().get('organic_results', [])
    position = pd.DataFrame({'position': [entry['position'] for entry in organic_results]})
    title = pd.DataFrame({'title': [entry['title'] for entry in organic_results]})
    link = pd.DataFrame({'link': [entry['link'] for entry in organic_results]})

    df = pd.concat([df, position, title, link], axis=1)
    df['date'] = df['date'].ffill()
    df['query'] = df['query'].ffill()
    df['engine'] = df['engine'].ffill()

    return df


# Function to process Google and Baidu search results
# def process_google_baidu_search(search, df=None):
    date = search.get_dict()['search_metadata']['created_at']
    query = search.get_dict()['search_parameters']['q']
    engine = search.get_dict()['search_parameters']['engine']

    if df is None:
        data = {'date': [date], 'query': [query], 'engine': [engine]}
        df = pd.DataFrame(data)

    organic_results = search.get_dict().get('organic_results', [])
    position = pd.DataFrame({'position': [entry['position'] for entry in organic_results]})
    title = pd.DataFrame({'title': [entry['title'] for entry in organic_results]})
    link = pd.DataFrame({'link': [entry['link'] for entry in organic_results]})
    date_result = pd.DataFrame({'date_result': [entry.get('date') for entry in organic_results]})
    source = pd.DataFrame({'source': [entry.get('source') or re.match(r'https?://(?:www\.)?([^/]+)', entry['link']).group(1) if entry.get('link') and re.match(r'https?://', entry['link']) else 'Unknown' for entry in organic_results]})

    df = pd.concat([df, position, title, link, date_result, source], axis=1)
    df['date'] = df['date'].ffill()
    df['query'] = df['query'].ffill()
    df['engine'] = df['engine'].ffill()

    return df

# Function to process Yandex search results
def process_yandex_search(search, df=None):
    date = search.get_dict()['search_metadata']['created_at']
    query = search.get_dict()['search_parameters']['text']
    engine = search.get_dict()['search_parameters']['engine']

    if df is None:
        data = {'date': [date], 'query': [query], 'engine': [engine]}
        df = pd.DataFrame(data)

    organic_results = search.get_dict().get('organic_results', [])
    position = pd.DataFrame({'position': [entry['position'] for entry in organic_results]})
    title = pd.DataFrame({'title': [entry['title'] for entry in organic_results]})
    link = pd.DataFrame({'link': [entry['link'] for entry in organic_results]})
    date_result = pd.DataFrame({'date_result': [entry.get('date') for entry in organic_results]})
    source = pd.DataFrame({'source': [entry.get('displayed_link') or entry.get('displayed_brand') or re.match(r'https?://(?:www\.)?([^/]+)', entry['link']).group(1) if entry.get('link') and re.match(r'https?://', entry['link']) else 'Unknown' for entry in organic_results]})

    df = pd.concat([df, position, title, link, date_result, source], axis=1)
    df['date'] = df['date'].ffill()
    df['query'] = df['query'].ffill()
    df['engine'] = df['engine'].ffill()

    return df

# Function to process Google News search results
def process_google_news_search(search, df=None):
    search_data = search.get_dict()
    metadata = search_data['search_metadata']
    parameters = search_data['search_parameters']
    
    date = metadata['created_at']
    query = parameters['q']
    engine = parameters['engine']

    positions = []
    titles = []
    links = []
    dates = []
    sources = []

    news_results = search_data.get('news_results', [])
    for entry in news_results:
        if 'stories' in entry:
            for story in entry['stories']:
                positions.append(entry['position'])
                titles.append(story['title'])
                links.append(story['link'])
                dates.append(story.get('date'))
                sources.append(story['source']['name'])
        else:
            positions.append(entry['position'])
            titles.append(entry['title'])
            links.append(entry['link'])
            dates.append(entry.get('date'))
            sources.append(entry['source']['name'])

    news_df = pd.DataFrame({
        'position': positions,
        'title': titles,
        'link': links,
        'date_result': dates,
        'source': sources,
        'date': date,
        'query': query,
        'engine': engine
    })

    if df is None:
        df = news_df
    else:
        df = pd.concat([df, news_df], ignore_index=True)

    return df

# Function to perform search with pagination
def perform_search(query_list, engine, timeframe=None, max_results=100):
    all_results = []
    results_per_page = 100

    for query in query_list:
        query_results = []
        start_value = 0 if engine != "yandex" else 0  # Yandex uses 'p' for pagination
        params = {
            "engine": engine,
            "api_key": API_KEY,
            "num": results_per_page if engine != "yandex" else None,
        }
        if engine == "naver":
            params["where"] = "web"
            params["q"] = query
        elif engine == "yandex":
            params["text"] = query
            params["yandex_domain"] = "yandex.com"
            params["lang"] = "en"
            params["lr"] = "84"
            params["p"] = start_value
        elif engine == "google_news":
            params["q"] = query
            params["tbm"] = "nws"
            if timeframe:
                params["tbs"] = f"qdr:{timeframe}"
        else:
            params["q"] = query

        while len(query_results) < max_results:
            try:
                if engine == "yandex":
                    params["p"] = start_value
                else:
                    params["start"] = start_value
                search = GoogleSearch(params)
                json_response = search.get_dict()

                if engine == "naver":
                    temp_df = process_naver_web_search(search)
                elif engine == "google_news":
                    temp_df = process_google_news_search(search)
                elif engine == "yandex":
                    temp_df = process_yandex_search(search)
                else:
                    temp_df = process_google_baidu_search(search)

                query_results.append(temp_df)

                next_link = json_response.get('serpapi_pagination', {}).get('next')
                if not next_link:
                    break
                match = re.search(r'(?:start|p)=(\d+)', next_link)
                if match:
                    start_value = int(match.group(1))
                else:
                    break
                time.sleep(1)  # Avoid rate limiting
            except Exception as e:
                print(f"Error in performing search for query '{query}': {e}")
                break

        all_results.extend(query_results)

    if all_results:
        return pd.concat(all_results, ignore_index=True)
    return pd.DataFrame()

@app.route('/', methods=['GET', 'POST'])
def index():
    results_df = None
    if request.method == 'POST':
        # Get form data
        engine = request.form.get('engine')
        timeframe = request.form.get('timeframe')
        queries = request.form.get('queries').split('\n')
        queries = [q.strip() for q in queries if q.strip()]

        if queries:
            # Perform search
            results_df = perform_search(queries, engine, timeframe)
            # Convert DataFrame to HTML
            if not results_df.empty:
                # Ensure links are clickable
                results_df['link'] = results_df['link'].apply(lambda x: f'<a href="{x}" target="_blank">{x}</a>')
                results_html = results_df.to_html(escape=False, index=False, classes='table table-striped')
            else:
                results_html = "<p>No results found.</p>"
        else:
            results_html = "<p>Please enter at least one search term.</p>"
    else:
        results_html = ""

    return render_template('index.html', results=results_html)

if __name__ == '__main__':
    app.run(debug=True)
