import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "2(x+4) = 20"
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
    # We do NOT replace 2x with 2*x manually anymore. 
    # The new smart_parse function handles that!
    return text

def smart_parse(text, evaluate=True):
    """
    The 'Human' Parser.
    1. Handles implicit multiplication (2x -> 2*x).
    2. Handles evaluate=False (prevents 2(x+4) turning into 2x+8 in visuals).
    """
    # Define the transformations (rules) for the parser
    # "implicit_multiplication_application" allows '2x' and '2(x+4)'
    transformations = (standard_transformations + (implicit_multiplication_application,))
    
    try:
        if "=" in text:
            parts = text.split("=")
            # Parse LHS and RHS separately
            lhs = parse_expr(parts[0], transformations=transformations, evaluate=evaluate)
            rhs = parse_expr(parts[1], transformations=transformations, evaluate=evaluate)
            return Eq(lhs, rhs)
        else:
            return parse_expr(text, transformations=transformations, evaluate=evaluate)
    except Exception as e:
        # Fallback if something is really weird
        return sympify(text, evaluate=evaluate)

def pretty_print(math_str):
    try:
        clean_str = clean_input(math_str)
        clean_str = clean_str.replace("±", "±")
        
        # KEY FIX: evaluate=False stops the engine from solving distribution in the preview
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def diagnose_error(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        # We need values to compare
        eq_prev = smart_parse(clean_input(line_prev_str))
        eq_curr = smart_parse(clean_input(line_curr_str))
        
        sol_prev = solve(eq_prev, x)
        sol_curr = solve(eq_curr, x)
        
        if not sol_prev or not sol_curr:
             return "I'm confused. Please check your syntax."

        # Get the numbers
        val_prev = sol_prev[0]
        val_curr = sol_curr[0]
        
        # Calculate the difference
        diff = val_curr - val_prev
        
        # --- THE HINT LOGIC ---
        if diff != 0:
            return f"The math doesn't match. (Difference: {diff}). Check your signs or operations."
            
        return "Logic error."
    except:
        return "Check your math logic."

def validate_step(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        # Use smart_parse with evaluate=True for the MATH CHECK
        eq1 = smart_parse(clean_input(line_prev_str), evaluate=True)
        sol1 = solve(eq1, x)
        correct_set = set(sol1)

        user_set = set()
        clean_curr = clean_input(line_curr_str)
        
        if "±" in clean_curr:
            parts = clean_curr.split("±")
            val = smart_parse(parts[1].strip(), evaluate=True)
            user_set.add(val)
            user_set.add(-val)
        elif "," in clean_curr:
            rhs = clean_curr.split("=")[1] if "=" in clean_curr else clean_curr
            vals = rhs.split(",")
            for v in vals:
                if v.strip(): user_set.add(smart_parse(v.strip(), evaluate=True))
        elif "=" in clean_curr:
            eq2 = smart_parse(clean_curr, evaluate=True)
            sol2 = solve(eq2, x)
            user_set = set(sol2)
        else:
            if clean_curr.strip():
                 try:
                    user_set.add(smart_parse(clean_curr.strip(), evaluate=True))
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

st.set_page_config(page_title="Step-Checker v1.3", page_icon="🧮")
st.title("🧮 Step-Checker v1.3")

# Sidebar
with st.sidebar:
    st.header("📝 Session Log")
    if st.session_state.history:
        st.write(f"Problems Checked: **{len(st.session_state.history)}**")
        df = pd.DataFrame(st.session_state.history)
        csv = convert_df_to_csv(df)
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
    
    # RESTORED: Socratic Hint Logic
    hint_message = ""
    if not is_valid:
        hint_message = diagnose_error(line_a, line_b)

    # LOG RESULT
    now = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.history.append({
        "Time": now,
        "Input A": line_a,
        "Input B": line_b,
        "Result": status,
        "Hint Given": hint_message # Added hint to CSV too!
    })
    
    if is_valid and status == "Valid":
        st.success("✅ **Perfect Logic!**")
        st.balloons()
    elif is_valid and status == "Partial":
        st.warning("⚠️ **Technically Correct, but Incomplete.**")
        st.write("You found one valid solution, but you missed the other root.")
    else:
        # RESTORED: Error display
        st.error("❌ **Logic Break**")
        st.info(f"💡 {hint_message}")

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
