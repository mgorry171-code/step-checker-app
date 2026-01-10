import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex, N, reduce_inequalities
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd
import re

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "2x + 5 < 15"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""
if 'history' not in st.session_state:
    st.session_state.history = []
if 'keypad_target' not in st.session_state:
    st.session_state.keypad_target = "Current Line"

# --- HELPER FUNCTIONS ---
def add_to_input(text_to_add):
    if st.session_state.keypad_target == "Previous Line":
        st.session_state.line_prev += text_to_add
    else:
        st.session_state.line_curr += text_to_add

def clean_input(text):
    text = text.lower()
    
    # 1. Thousands separators
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)

    # 2. Basic Replacements
    text = text.replace(" and ", ",")
    text = text.replace("^", "**")
    text = text.replace("+/-", "±")
    text = text.replace("%", "/100")
    text = text.replace(" of ", "*")
    
    # 3. Inequality Standardization
    text = text.replace("=<", "<=").replace("=>", ">=")
    
    return text

def smart_parse(text, evaluate=True):
    transformations = (standard_transformations + (implicit_multiplication_application,))
    try:
        # Check for Inequality operators
        if "<=" in text or ">=" in text or "<" in text or ">" in text:
            return parse_expr(text, transformations=transformations, evaluate=evaluate)
            
        # Check for Equation (=)
        elif "=" in text:
            parts = text.split("=")
            lhs = parse_expr(parts[0], transformations=transformations, evaluate=evaluate)
            rhs = parse_expr(parts[1], transformations=transformations, evaluate=evaluate)
            return Eq(lhs, rhs)
            
        else:
            return parse_expr(text, transformations=transformations, evaluate=evaluate)
    except:
        return sympify(text, evaluate=evaluate)

def pretty_print(math_str):
    try:
        clean_str = clean_input(math_str)
        clean_str = clean_str.replace("±", "±")
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def get_solution_set(text_str):
    """
    Solves Equations AND Inequalities. Returns a SymPy Set.
    """
    x = symbols('x')
    clean = clean_input(text_str)
    
    try:
        # Case A: "+/-" syntax
        if "±" in clean:
            parts = clean.split("±")
            val = smart_parse(parts[1].strip(), evaluate=True)
            return sympy.FiniteSet(val, -val)
            
        # Case B: Comma list (FiniteSet)
        elif "," in clean:
            rhs = clean.split("=")[1] if "=" in clean else clean
            items = rhs.split(",")
            vals = []
            for i in items:
                if i.strip():
                    vals.append(smart_parse(i.strip(), evaluate=True))
            return sympy.FiniteSet(*vals)
            
        # Case C: Single Expression/Equation/Inequality
        else:
            expr = smart_parse(clean, evaluate=True)
            
            # If it's an Equation or Expression
            if isinstance(expr, Eq) or not (expr.is_Relational):
                if not isinstance(expr, Eq): pass 
                return sympy.solve(expr, x, set=True)[1] 
            
            # If it's an Inequality
            else:
                solution = reduce_inequalities(expr, x)
                return solution.as_set()
                
    except Exception as e:
        return None

def validate_step(line_prev_str, line_curr_str):
    try:
        if not line_prev_str or not line_curr_str:
            return False, "Empty"

        set_A = get_solution_set(line_prev_str)
        set_B = get_solution_set(line_curr_str)
        
        if set_A is None and line_prev_str: return False, "Could not solve Line A"
        if set_B is None: return False, "Could not parse Line B"

        # 1. Exact Set Match
        if set_A == set_B:
            return True, "Valid"
        
        # 2. Subset (Partial Credit)
        if set_B.is_subset(set_A) and not set_B.is_empty:
            return True, "Partial"
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

# --- WEB INTERFACE ---

st.set_page_config(page_title="The Logic Lab v2.1", page_icon="🧪")
st.title("🧪 The Logic Lab (v2.1)")

with st.sidebar:
    st.header("📝 Session Log")
    if st.session_state.history:
        st.write(f"Problems Checked: **{len(st.session_state.history)}**")
        df = pd.DataFrame(st.session_state.history)
        csv = convert_df_to_csv(df)
        st.download_button("📊 Download Excel/CSV", csv, "Math_Session.csv", "text/csv")
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()

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

st.markdown("---")
st.radio("Keypad Target:", ["Previous Line", "Current Line"], horizontal=True, key="keypad_target", label_visibility="visible")

# --- UPDATED KEYPAD (6 COLUMNS) ---
st.markdown("##### ⌨️ Quick Keys")
k1, k2, k3, k4, k5, k6 = st.columns(6) # 6 Columns now
k1.button("x²", on_click=add_to_input, args=("^2",)) 
k2.button("±", on_click=add_to_input, args=("+/-",)) 
k3.button("<", on_click=add_to_input, args=("<",))  # Added Less Than
k4.button(">", on_click=add_to_input, args=(">",)) 
k5.button("≤", on_click=add_to_input, args=("<=",)) 
k6.button("≥", on_click=add_to_input, args=(">=",)) 

st.markdown("---")

if st.button("Check Logic", type="primary"):
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    
    is_valid, status = validate_step(line_a, line_b)
    
    now = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.history.append({
        "Time": now, "Input A": line_a, "Input B": line_b, "Result": status
    })
    
    if is_valid and status == "Valid":
        st.success("✅ **Perfect Logic!**")
        st.balloons()
    elif is_valid and status == "Partial":
        st.warning("⚠️ **Technically Correct, but Incomplete.**")
    else:
        st.error("❌ **Logic Break**")

st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: #666;'><small>Built by The Logic Lab 🧪 | © 2026 Step-Checker</small></div>""",
    unsafe_allow_html=True
)
