# app.py (FINAL, COMPLETE, AND STABLE VERSION)

import dash
from dash import dcc, html
# CORRECT IMPORTS for modern Dash (resolves all previous import errors)
from dash import Dash, Input, Output, State, callback 
import pandas as pd
import plotly.express as px

# Import custom modules 
from user_data import fetch_rda, register_new_user, get_all_users
# app.py (Replace with these correct lines)
from llm_processor import get_llm_meal_interpretation
from user_data import fetch_nutrient_data # <-- Now correctly imported from user_data
# --- APP INITIALIZATION ---
# Load USER_DATA from SQLite at startup by calling the function
USER_DATA = get_all_users() 

# suppress_callback_exceptions=True is necessary for multi-page/hidden DIV structures
app = Dash(__name__, title="Nutrition Dashboard", suppress_callback_exceptions=True)


# --------------------------------------------------------------------
# A. LAYOUT FUNCTIONS
# --------------------------------------------------------------------

# Shared Navigation Bar
def get_nav_bar(user_id):
    # Reload USER_DATA every time the nav bar is created 
    global USER_DATA
    USER_DATA = get_all_users()
    
    username = user_id
    user = USER_DATA.get(username, {})
    return html.Div([
        html.H2(f"Welcome, {user.get('name', 'User')}!", style={'display': 'inline-block', 'marginRight': '30px'}),
        dcc.Link('Log Meal', href='/log', style={'padding': '10px'}),
        dcc.Link('Analysis', href='/analysis', style={'padding': '10px'}),
        dcc.Link('Suggestions', href='/suggestions', style={'padding': '10px'}),
        dcc.Link('Profile', href='/profile', style={'padding': '10px'}),
        html.Button('Logout', id='logout-button', n_clicks=0, style={'float': 'right'})
    ], style={'borderBottom': '2px solid #ddd', 'marginBottom': '20px', 'paddingBottom': '10px'})

# 1. Login Page Layout
def get_login_layout(error=None):
    """Generates the Login form layout."""
    error_div = html.Div(error, style={'color': 'red', 'marginTop': '10px'}) if error else None
    return html.Div([
        html.H1("Nutrition Tracker Login", style={'textAlign': 'center'}),
        html.Div([
            dcc.Input(id='login-username', type='text', placeholder='Username', style={'margin': '5px'}),
            dcc.Input(id='login-password', type='password', placeholder='Password', style={'margin': '5px'}),
            html.Button('Login', id='login-button', n_clicks=0, style={'margin': '10px'}),
            html.Button('New User? Register', id='register-switch-button', n_clicks=0, style={'margin': '10px', 'backgroundColor': '#f0ad4e', 'color': 'white'}),
            html.Div(id='login-output-status', children=error_div),
        ], style={'maxWidth': '400px', 'margin': '50px auto', 'padding': '20px', 'border': '1px solid #ccc', 'textAlign': 'center'})
    ], id='auth-container')

# 2. Registration Page Layout
def get_register_layout(error=None):
    error_div = html.Div(error, style={'color': 'red', 'marginTop': '10px'}) if error else None
    return html.Div([
        html.H1("Create New Account", style={'textAlign': 'center'}),
        html.Div([
            dcc.Input(id='reg-username', type='text', placeholder='Choose Username', style={'margin': '5px'}),
            dcc.Input(id='reg-password', type='password', placeholder='Choose Password', style={'margin': '5px'}),
            dcc.Input(id='reg-name', type='text', placeholder='Your Name', style={'margin': '5px'}),
            dcc.Input(id='reg-age', type='number', placeholder='Age', style={'margin': '5px'}),
            dcc.Dropdown(id='reg-gender', placeholder='Gender', options=[{'label': 'Male', 'value': 'Male'}, {'label': 'Female', 'value': 'Female'}], style={'margin': '5px'}),
            dcc.Dropdown(id='reg-activity-level', placeholder='Activity Level', options=[
                {'label': 'Sedentary', 'value': 'SEDENTARY'}, 
                {'label': 'Moderate', 'value': 'MODERATE'}, 
                {'label': 'Active', 'value': 'ACTIVE'}
            ], value='SEDENTARY', style={'margin': '5px'}),
            html.Button('Submit Registration', id='register-submit-button', n_clicks=0, style={'margin': '10px', 'backgroundColor': '#5cb85c', 'color': 'white'}),
            html.Button('Back to Login', id='login-switch-button', n_clicks=0, style={'margin': '10px'}),
            error_div,
        ], style={'maxWidth': '400px', 'margin': '50px auto', 'padding': '20px', 'border': '1px solid #ccc', 'textAlign': 'center'})
    ], id='auth-container')

# 3. Profile Page Layout
def get_profile_layout(user_id):
    global USER_DATA
    USER_DATA = get_all_users()
    
    user = USER_DATA.get(user_id, {})
    return html.Div([
        get_nav_bar(user_id),
        html.H2("👤 User Profile"),
        html.Div([
            html.P(html.B("Name: "), f"{user.get('name', 'N/A')}"),
            html.P(html.B("Age: "), f"{user.get('age', 'N/A')}"),
            html.P(html.B("Gender: "), f"{user.get('gender', 'N/A')}"),
            html.P(html.B("Activity Level: "), f"{user.get('activity_level', 'N/A')}"),
        ], style={'padding': '20px', 'border': '1px solid #eee'})
    ])

# 4. Log Meal Page Layout 
def get_log_meal_layout():
    return html.Div([
        html.H2("🍽️ Log Meal (LLM Input)", style={'color': '#1f77b4'}),
        dcc.Textarea(
            id='meal-description-input',
            placeholder='Describe your meal (e.g., "A sandwich with turkey and mayo" or "oatmeal")',
            style={'width': '100%', 'height': 80, 'padding': '10px'}
        ),
        html.Button('Interpret & Log Meal', id='add-meal-button', n_clicks=0, style={'margin': '10px 0', 'backgroundColor': '#2ca02c', 'color': 'white'}),
        
        html.Div(id='confirmation-review', style={'marginTop': '10px', 'padding': '10px', 'borderLeft': '3px solid #ccc'}),
        
        html.H3("Current Logged Items"),
        html.Div(id='intake-summary-output', style={'border': '1px dashed #ccc', 'padding': '10px'})
    ])

# 5. Analysis Logic (Helper Function)
def perform_analysis(intake_df: pd.DataFrame, activity_level: str):
    if intake_df.empty:
        return pd.DataFrame(), "No intake data logged yet."

    numeric_intake = intake_df.drop(columns=['Item', 'Quantity'], errors='ignore')
    total_intake = numeric_intake.sum()
    
    rda_values = pd.Series(fetch_rda(activity_level)).reindex(total_intake.index, fill_value=0)
    
    comparison_df = pd.DataFrame({
        'Nutrient': total_intake.index,
        'Intake': total_intake.values,
        'RDA': rda_values.values
    })
    
    comparison_df['% RDA'] = (comparison_df['Intake'] / comparison_df['RDA']).replace([float('inf'), float('-inf')], 1).fillna(0) * 100
    
    low_nutrients = comparison_df[comparison_df['% RDA'] < 80]
    suggestions = "No major deficiencies detected! Keep logging your meals."
    if not low_nutrients.empty:
        suggestions = "⚠️ **Deficiency Alert!** You are low on: "
        for index, row in low_nutrients.iterrows():
            suggestions += f"{row['Nutrient']} ({row['% RDA']:.0f}% of RDA). "
        suggestions += "\n\n*Suggestion:* Based on our mock data, try combining items like 'oatmeal' (for fiber/iron) and 'eggs' (for protein/calories)."
    
    return comparison_df, suggestions

# 6. Analysis Page Layout
def get_analysis_layout(user_id, intake_data_list):
    global USER_DATA
    USER_DATA = get_all_users()
    
    user_data = USER_DATA[user_id]
    activity_level = user_data['activity_level']
    
    if not intake_data_list:
        empty_fig = px.bar(title="Log a meal to view nutritional analysis.")
        return html.Div([
              get_nav_bar(user_id),
              html.H2("📊 Analysis Dashboard"),
              dcc.Graph(figure=empty_fig)
        ])
        
    intake_df = pd.DataFrame(intake_data_list)
    comparison_df, _ = perform_analysis(intake_df, activity_level)

    fig = px.bar(
        comparison_df, 
        x='Nutrient', 
        y=['Intake', 'RDA'],
        barmode='group',
        title=f"Intake vs. RDA ({activity_level})",
        labels={'value': 'Amount (g/Cal/mg)', 'variable': 'Category'},
        height=400
    )
    return html.Div([
        get_nav_bar(user_id),
        html.H2("📊 Analysis Dashboard"),
        dcc.Graph(figure=fig)
    ])

# 7. Suggestions Page Layout
def get_suggestions_layout(user_id, intake_data_list):
    global USER_DATA
    USER_DATA = get_all_users()
    
    user_data = USER_DATA[user_id]
    activity_level = user_data['activity_level']
    
    if not intake_data_list:
        suggestions_output = "Log your first meal to see a personalized suggestion."
    else:
        intake_df = pd.DataFrame(intake_data_list)
        _, suggestions_text = perform_analysis(intake_df, activity_level)
        suggestions_output = html.Div(
            [html.P(line) for line in suggestions_text.split('\n')],
            style={'whiteSpace': 'pre-line', 'backgroundColor': '#f0f0f0', 'padding': '15px', 'borderRadius': '5px'}
        )
        
    return html.Div([
        get_nav_bar(user_id),
        html.H2("💡 Suggested Actions"),
        suggestions_output
    ])

# --------------------------------------------------------------------
# B. MAIN LAYOUT & ROUTING 
# --------------------------------------------------------------------

app.layout = html.Div([
    dcc.Location(id='url', refresh=False), 
    dcc.Store(id='session-user-id', data=None), 
    dcc.Store(id='daily-intake-store', data=[]), 
    html.Div(id='page-content', style={'maxWidth': '900px', 'margin': '0 auto', 'fontFamily': 'Arial, sans-serif'})
])

# --------------------------------------------------------------------
# C. CALLBACKS 
# --------------------------------------------------------------------

# 1. Router Callback
@callback(Output('page-content', 'children'),
          [Input('url', 'pathname'),
           Input('session-user-id', 'data'),
           Input('daily-intake-store', 'data')])
def display_page(pathname, user_id, intake_data_list):
    global USER_DATA
    USER_DATA = get_all_users()

    if user_id is None:
        if pathname == '/register':
            return get_register_layout()
        # Default to login page if no user is logged in
        return get_login_layout()
    
    # User is logged in, show the requested page
    if pathname == '/profile':
        return get_profile_layout(user_id)
    elif pathname == '/analysis':
        return get_analysis_layout(user_id, intake_data_list)
    elif pathname == '/suggestions':
        return get_suggestions_layout(user_id, intake_data_list)
    # Default page for logged-in users is /log
    return html.Div([
        get_nav_bar(user_id),
        get_log_meal_layout()
    ])

# 2. Login/Logout Logic (Updates session-user-id store)
@callback(
    # Only outputs session ID and status. URL output is removed to prevent conflicts.
    [Output('session-user-id', 'data', allow_duplicate=True),
     Output('login-output-status', 'children')],
    [Input('login-button', 'n_clicks'),
     Input('logout-button', 'n_clicks')],
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def handle_login_logout(login_n, logout_n, username, password):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    global USER_DATA
    USER_DATA = get_all_users()
    
    if trigger_id == 'logout-button':
        # Logout logic
        return None, '' 
        
    if username in USER_DATA and USER_DATA[username]['password'] == password:
        # Successful login
        return username, ''
    else:
        # Failed login
        return None, html.Div("Invalid username or password", style={'color': 'red'})

# 3. Dedicated Redirection (Fixes 'Duplicate callback outputs' error)
@callback(
     Output('url', 'pathname', allow_duplicate=True),
     Input('session-user-id', 'data'),
     prevent_initial_call=True
)
def redirect_after_auth(user_id):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
        
    # Triggered by login/logout setting user_id
    if user_id is None:
        return '/' # Redirect to login page
    else:
        return '/log' # Redirect to log meal page

# 4. Registration Switch (To /register URL)
@callback(Output('url', 'pathname', allow_duplicate=True),[Input('register-switch-button', 'n_clicks')],prevent_initial_call=True)
def switch_to_register_view(reg_n):
    return '/register'

# 5. Login Switch (To / URL)
@callback(Output('url', 'pathname', allow_duplicate=True),[Input('login-switch-button', 'n_clicks')],prevent_initial_call=True)
def switch_to_login_view(login_n):
    return '/'

# 6. Registration Submission Logic (Updates URL on success/failure)
@callback(
    # Updates URL and Page Content (the success/error message in the next layout)
    [Output('url', 'pathname', allow_duplicate=True), 
     Output('page-content', 'children', allow_duplicate=True)], 
    [Input('register-submit-button', 'n_clicks')],
    [State('reg-username', 'value'),State('reg-password', 'value'),State('reg-name', 'value'),
     State('reg-age', 'value'),State('reg-gender', 'value'),State('reg-activity-level', 'value')],
    prevent_initial_call=True
)
def handle_registration_submission(n_clicks, username, password, name, age, gender, activity_level):
    
    # 1. Validation Check (If any field is missing)
    if not all([username, password, name, age, gender, activity_level]):
        return '/register', get_register_layout(error="All fields are required.")

    # 2. Database Action
    success, message = register_new_user(username, password, name, age, gender, activity_level)
    
    if success:
        # On success, navigate to the Login page ('/') and pass the success message
        return '/', get_login_layout(error=html.Div(message + " You can now log in.", style={'color': 'green'}))
    else:
        # On registration error (e.g., username taken), stay on the registration page and display error
        return '/register', get_register_layout(error=message)


# 7. Log Meal Callback 
@callback(
    [Output('daily-intake-store', 'data', allow_duplicate=True),
     Output('confirmation-review', 'children'),
     Output('meal-description-input', 'value')], 
    [Input('add-meal-button', 'n_clicks')],
    [State('meal-description-input', 'value'),
     State('daily-intake-store', 'data')],
    prevent_initial_call=True
)
def handle_meal_submission(n_clicks, meal_description, current_intake_list):
    if not meal_description:
        return current_intake_list, html.P("Please enter a meal description.", style={'color': 'red'}), dash.no_update

    # 1. Interpret Meal using Gemini API
    structured_items = get_llm_meal_interpretation(meal_description)
    
    new_meal_data = []
    found_items_list = []
    
    # 2. Fetch Nutrients for each item (using the internal mock data)
    for item in structured_items:
        nutrients = fetch_nutrient_data(item['food_name'], item['quantity_g']) 
        if not nutrients.empty:
            new_meal_data.append(nutrients.to_dict())
            found_items_list.append(f"{item['food_name']} ({item['quantity_g']}g)")

    if not new_meal_data:
        # This occurs if Gemini returns un-matchable items, or if the API key is missing
        return current_intake_list, html.P(
            f"Could not find nutrient data for any item. Check your Gemini API key, or use foods like 'eggs', 'rice', 'oatmeal', 'bread', or 'chicken'.", 
            style={'color': 'orange'}
        ), meal_description

    updated_intake_list = current_intake_list + new_meal_data
    
    confirmation_msg = html.Div([
        html.P("✅ Meal Logged Successfully!", style={'fontWeight': 'bold', 'color': 'green'}),
        html.Ul([html.Li(item) for item in found_items_list])
    ])

    return updated_intake_list, confirmation_msg, "" 

# 8. Update Intake Summary Output
@callback(
    Output('intake-summary-output', 'children'),
    Input('daily-intake-store', 'data')
)
def display_intake_summary(intake_data_list):
    if not intake_data_list:
        return html.P("No meals logged for this session yet.")
    
    return html.Ul([
        html.Li(f"{d['Item']} ({d['Quantity']}g)") for d in intake_data_list
    ])


if __name__ == '__main__':
    print("Dashboard starting at http://127.0.0.1:8050/")
    # FINAL FIX: Use app.run() instead of app.run_server()
    app.run(debug=True)