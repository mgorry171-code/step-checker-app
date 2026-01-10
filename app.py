import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex, N
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd
import re # NEW: Library for pattern matching (Regex)

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "900 + 100 = x"
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
    
    # NEW: Remove thousands separators (e.g., 1,000 -> 1000)
    # Logic: Look for a digit, a comma, and exactly 3 digits
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    # Run it twice to catch millions (1,000,000 -> 1000,000 -> 1000000)
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)

    text = text.replace(" and ", ",")
    text = text.replace("^", "**")
    text = text.replace("+/-", "±")
    text = text.replace("%", "/100")
    text = text.replace(" of ", "*")
    return text

def smart_parse(text, evaluate=True):
    transformations = (standard_transformations + (implicit_multiplication_application,))
    try:
        if "=" in text:
            parts = text.split("=")
            lhs_text = parts[0].strip()
            rhs_text = parts[1].strip()
            
            lhs = parse_expr(lhs_text, transformations=transformations, evaluate=evaluate)
            rhs = parse_expr(rhs_text, transformations=transformations, evaluate=evaluate)
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
            # Note: 1,000 has already been cleaned to 1000 by clean_input
            # So this comma check only catches actual lists like "4, -4"
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
    try:
        float_a = set()
        for item in set_a:
            try: float_a.add(float(N(item)))
            except: pass
            
        float_b = set()
        for item in set_b:
            try: float_b.add(float(N(item)))
            except: pass
            
        if not float_a or not float_b: return False
        if len(float_a) != len(float_b): return False
            
        matches = 0
        for val_b in float_b:
            for val_a in float_a:
                if abs(val_b - val_a) < 1e-9:
                    matches += 1
                    break
        return matches == len(float_a)
    except:
        return False

def validate_step(line_prev_str, line_curr_str):
    try:
        if not line_prev_str or not line_curr_str:
            return False, "Empty"

        correct_set = extract_values(line_prev_str)
        user_set = extract_values(line_curr_str)
        
        if not correct_set and line_prev_str: 
            return False, "Could not solve Line A"
            
        if correct_set == user_set: return True, "Valid"
        if check_numerical_match(correct_set, user_set): return True, "Valid"
        if user_set.issubset(correct_set) and len(user_set) > 0: return True, "Partial"
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v1.8", page_icon="🧮")
st.title("🧮 Step-Checker v1.8")

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
    
    hint = "Values do not match." if not is_valid else ""

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
