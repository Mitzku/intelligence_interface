from flask import Flask, request, render_template
import pandas as pd
from utils.search_functions import perform_google_search



app = Flask(__name__)

API_KEY = "f6d8379e68815bc7a18d1680ea24398ef22d50da7c7b56f06726e639a2e212ea"


@app.route('/', methods=['GET', 'POST'])
def index():
    search_results = None
    error = None
    
    if request.method == 'POST':
        try:
            engine = request.form.get('engine', 'google')
            query_list = [q.strip() for q in request.form.get('queries', '').split('\n') if q.strip()]
            max_results = int(request.form.get('number_results', '100'))

            params = {
                "engine": engine,
                "api_key": API_KEY
            }

            search_results_list = perform_google_search(query_list, params, max_results)
            
            if search_results_list:
                # Concatenate all DataFrames from the nested list
                concatenated_df = pd.concat([df for query_results in search_results_list for df in query_results], ignore_index=True)
                # Convert DataFrame to HTML table for display
                search_results = concatenated_df.to_html(classes='table table-striped', index=False)
            else:
                error = "No results found"
                
        except Exception as e:
            error = f"An error occurred: {str(e)}"

    return render_template('index.html', search_results=search_results, error=error)

if __name__ == '__main__':
    app.run(debug=True)

