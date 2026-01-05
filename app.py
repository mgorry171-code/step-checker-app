import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex
import datetime
import pandas as pd # NEW: The library that handles spreadsheets

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x**2 = 16"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""
if 'history' not in st.session_state:
    st.session_state.history = []

# --- HELPER FUNCTIONS ---
def add_to_curr(text_to_add):
    st.session_state.line_curr += text_to_add

def clean_input(text):
    text = text.replace(" and ", ",")
    text = text.replace("^", "**")
    text = text.replace("+/-", "±") 
    return text

def pretty_print(math_str):
    try:
        clean_str = clean_input(math_str)
        clean_str = clean_str.replace("±", "±") 
        if "=" in clean_str:
            lhs, rhs = clean_str.split("=")
            if "," in rhs:
                return f"{latex(sympify(lhs.strip()))} = {rhs.strip()}"
            return f"{latex(sympify(lhs.strip()))} = {latex(sympify(rhs.strip()))}"
        else:
            return latex(sympify(clean_str))
    except:
        return None

# NEW: CSV GENERATOR
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def validate_step(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        clean_prev = clean_input(line_prev_str)
        if "=" in clean_prev:
            lhs, rhs = clean_prev.split("=")
            eq1 = Eq(sympify(lhs.strip()), sympify(rhs.strip()))
        else:
            eq1 = sympify(clean_prev)

        sol1 = solve(eq1, x)
        correct_set = set(sol1)

        user_set = set()
        clean_curr = clean_input(line_curr_str)
        
        if "±" in clean_curr:
            parts = clean_curr.split("±")
            val = sympify(parts[1].strip())
            user_set.add(val)
            user_set.add(-val)
        elif "," in clean_curr:
            rhs = clean_curr.split("=")[1] if "=" in clean_curr else clean_curr
            vals = rhs.split(",")
            for v in vals:
                if v.strip(): user_set.add(sympify(v.strip()))
        elif "=" in clean_curr:
            lhs, rhs = clean_curr.split("=")
            eq2 = Eq(sympify(lhs.strip()), sympify(rhs.strip()))
            sol2 = solve(eq2, x)
            user_set = set(sol2)
        else:
            if clean_curr.strip():
                 try:
                    user_set.add(sympify(clean_curr.strip()))
                 except: pass

        if not line_prev_str or not line_curr_str:
            return False, "Empty"

        if correct_set == user_set:
            return True, "Valid"
        
        if user_set.issubset(correct_set) and len(user_set) > 0:
            return True, "Partial"
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v1.2", page_icon="🧮")
st.title("🧮 Step-Checker v1.2")

# Sidebar for History/Actions
with st.sidebar:
    st.header("📝 Session Log")
    if st.session_state.history:
        st.write(f"Problems Checked: **{len(st.session_state.history)}**")
        
        # Convert list of dicts to a Dataframe (Spreadsheet)
        df = pd.DataFrame(st.session_state.history)
        csv = convert_df_to_csv(df)
        
        # DOWNLOAD BUTTON (CSV)
        st.download_button(
            label="📊 Download Excel/CSV",
            data=csv,
            file_name="Math_Session.csv",
            mime="text/csv"
        )
        
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("No history yet.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Previous Line")
    st.text_input("Line A", key="line_prev", label_visibility="collapsed")
    if st.session_state.line_prev:
        st.latex(pretty_print(st.session_state.line_prev))

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    if st.session_state.line_curr:
        st.latex(pretty_print(st.session_state.line_curr))

st.markdown("##### ⌨️ Quick Keys")
k1, k2, k3, k4, k5 = st.columns(5)
k1.button("x²", on_click=add_to_curr, args=("**2",))
k2.button("±", on_click=add_to_curr, args=("+/-",)) 
k3.button("÷", on_click=add_to_curr, args=("/",))
k4.button("(", on_click=add_to_curr, args=("(",))
k5.button(")", on_click=add_to_curr, args=(")",))

st.markdown("---")

if st.button("Check Logic", type="primary"):
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    
    is_valid, status = validate_step(line_a, line_b)
    
    # LOG RESULT with Timestamp
    now = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.history.append({
        "Time": now,
        "Input A": line_a,
        "Input B": line_b,
        "Result": status
    })
    
    if is_valid and status == "Valid":
        st.success("✅ **Perfect Logic!**")
        st.balloons()
    elif is_valid and status == "Partial":
        st.warning("⚠️ **Technically Correct, but Incomplete.**")
        st.write("You found one valid solution, but you missed the other root.")
    else:
        st.error("❌ **Logic Break**")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <small>Built by a Math Teacher in NYC 🍎 | © 2026 Step-Checker</small>
    </div>
    """,
    unsafe_allow_html=True
)


