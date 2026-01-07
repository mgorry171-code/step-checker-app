import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex, N
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "5% of 30"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""
if 'history' not in st.session_state:
    st.session_state.history = []
if 'keypad_target' not in st.session_state:
    st.session_state.keypad_target = "Current Line" # Default target

# --- HELPER FUNCTIONS ---
def add_to_input(text_to_add):
    """Adds text to the currently selected target box."""
    if st.session_state.keypad_target == "Previous Line":
        st.session_state.line_prev += text_to_add
    else:
        st.session_state.line_curr += text_to_add

def clean_input(text):
    text = text.lower()
    text = text.replace(" and ", ",")
    text = text.replace("^", "**")
    text = text.replace("+/-", "±")
    text = text.replace("%", "/100")
    text = text.replace(" of ", "*")
    return text

def smart_parse(text, evaluate=True):
    transformations = (standard_transformations + (implicit_multiplication_application,))
    try:
        # If we are parsing for the PREVIEW (evaluate=False), we want to be very careful
        if not evaluate:
             # Basic Parse
             expr = parse_expr(text, transformations=transformations, evaluate=False)
             return expr
             
        # Normal Solving Parse
        if "=" in text:
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
        # evaluate=False should keep |-4| as |-4|
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def extract_values(text_str):
    x = symbols('x')
    vals = set()
    clean = clean_input(text_str)
    
    try:
        if "±" in clean:
            parts = clean.split("±")
            val = smart_parse(parts[1].strip(), evaluate=True)
            vals.add(val)
            vals.add(-val)
        elif "," in clean:
            rhs = clean.split("=")[1] if "=" in clean else clean
            items = rhs.split(",")
            for i in items:
                if i.strip():
                    vals.add(smart_parse(i.strip(), evaluate=True))
        elif "=" in clean:
            eq = smart_parse(clean, evaluate=True)
            sol = solve(eq, x)
            vals.update(sol)
        else:
            if clean.strip():
                vals.add(smart_parse(clean.strip(), evaluate=True))
    except Exception:
        pass
        
    return vals

def check_numerical_match(set_a, set_b):
    """
    Fallback Logic: If symbolic sets don't match, try converting everything to floats.
    This handles '1.5' (float) vs '3/2' (Rational).
    """
    try:
        # Convert set A to floats
        float_a = set()
        for item in set_a:
            try:
                float_a.add(float(N(item))) # N() forces numerical evaluation
            except: pass
            
        # Convert set B to floats
        float_b = set()
        for item in set_b:
            try:
                float_b.add(float(N(item)))
            except: pass
            
        # Check if empty (avoid false positives)
        if not float_a or not float_b:
            return False

        # Check for near-equality (tolerance)
        # We can't just do set_a == set_b with floats due to precision.
        # Simple check: Are sets same size?
        if len(float_a) != len(float_b):
            return False
            
        # Check every item in B is close to some item in A
        matches = 0
        for val_b in float_b:
            for val_a in float_a:
                if abs(val_b - val_a) < 1e-9: # 0.000000001 tolerance
                    matches += 1
                    break
        
        return matches == len(float_a)
        
    except:
        return False

def diagnose_error(line_prev_str, line_curr_str):
    # (Same diagnostic logic, simplified for brevity)
    return "Check your math logic."

def validate_step(line_prev_str, line_curr_str):
    try:
        if not line_prev_str or not line_curr_str:
            return False, "Empty"

        correct_set = extract_values(line_prev_str)
        user_set = extract_values(line_curr_str)
        
        if not correct_set and line_prev_str: 
            return False, "Could not solve Line A"
            
        # 1. Symbolic Match (Perfect)
        if correct_set == user_set:
            return True, "Valid"

        # 2. Numerical Match (The "Decimal Fallback")
        # This catches 1.5 vs 3/2
        if check_numerical_match(correct_set, user_set):
            return True, "Valid"
        
        # 3. Subset Match (Partial Credit)
        if user_set.issubset(correct_set) and len(user_set) > 0:
            return True, "Partial"
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v1.6", page_icon="🧮")
st.title("🧮 Step-Checker v1.6")

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

# --- NEW: KEYPAD TARGET SELECTOR ---
st.markdown("---")
# This Radio button lets you choose where the keys type!
target = st.radio("Keypad Target:", ["Previous Line", "Current Line"], horizontal=True, key="keypad_target")

st.markdown("##### ⌨️ Quick Keys")
k1, k2, k3, k4, k5 = st.columns(5)
k1.button("x²", on_click=add_to_input, args=("^2",)) 
k2.button("±", on_click=add_to_input, args=("+/-",)) 
k3.button("|x|", on_click=add_to_input, args=("abs(",))
k4.button("(", on_click=add_to_input, args=("(",))
k5.button(")", on_click=add_to_input, args=(")",))

st.markdown("---")

if st.button("Check Logic", type="primary"):
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    
    is_valid, status = validate_step(line_a, line_b)
    
    # Simple Hint Logic for display
    hint_message = ""
    if not is_valid: 
        hint_message = "Values do not match."

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

# --- FOOTER ---
st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: #666;'><small>Built by a Math Teacher in NYC 🍎 | © 2026 Step-Checker</small></div>""",
    unsafe_allow_html=True
)
