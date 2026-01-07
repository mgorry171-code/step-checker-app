import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x^2 = 16"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""
if 'history' not in st.session_state:
    st.session_state.history = []

# --- HELPER FUNCTIONS ---
def add_to_curr(text_to_add):
    st.session_state.line_curr += text_to_add

def clean_input(text):
    """
    Master cleaner:
    1. Lowercase everything (Fixes 'X' vs 'x')
    2. Swaps 'and' for ','
    3. Swaps '^' for '**'
    4. Swaps '+/-' for '±'
    """
    text = text.lower() # Force lowercase
    text = text.replace(" and ", ",")
    text = text.replace("^", "**")
    text = text.replace("+/-", "±")
    return text

def smart_parse(text, evaluate=True):
    """
    Parses text into SymPy expressions with implicit multiplication (2x -> 2*x).
    """
    transformations = (standard_transformations + (implicit_multiplication_application,))
    try:
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
        # evaluate=False prevents 2(x+4) from becoming 2x+8 in the preview
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def extract_values(text_str):
    """
    Robustly extracts a SET of numerical solutions from a string.
    Handles: "x=4", "4", "4, -4", "x=4, -4", "x = +/- 4"
    Returns: A Python set of SymPy numbers.
    """
    x = symbols('x')
    vals = set()
    clean = clean_input(text_str)
    
    try:
        # Case A: "+/-" syntax
        if "±" in clean:
            parts = clean.split("±")
            val = smart_parse(parts[1].strip(), evaluate=True)
            vals.add(val)
            vals.add(-val)
            
        # Case B: Comma list (4, -4)
        elif "," in clean:
            rhs = clean.split("=")[1] if "=" in clean else clean
            items = rhs.split(",")
            for i in items:
                if i.strip():
                    vals.add(smart_parse(i.strip(), evaluate=True))
                    
        # Case C: Equation or Single Expression
        elif "=" in clean:
            eq = smart_parse(clean, evaluate=True)
            sol = solve(eq, x)
            vals.update(sol)
            
        else:
            # Just a number "4"
            if clean.strip():
                vals.add(smart_parse(clean.strip(), evaluate=True))
                
    except Exception:
        pass # If extraction fails, we return whatever we found so far
        
    return vals

def diagnose_error(line_prev_str, line_curr_str):
    try:
        # 1. Get the "Correct" values from previous line
        correct_vals = extract_values(line_prev_str)
        # 2. Get the "Student" values from current line
        student_vals = extract_values(line_curr_str)
        
        if not correct_vals:
            return "I can't solve the previous line."
        if not student_vals:
            return "I can't understand your answer syntax."
            
        # Compare just one value to see if there is a predictable offset
        # (This is a simple heuristic)
        val_correct = list(correct_vals)[0]
        val_student = list(student_vals)[0]
        
        diff = val_student - val_correct
        
        if diff != 0:
            return f"The values don't match. (Difference: {diff}). Check signs or arithmetic."
            
        return "Logic error."
    except:
        return "Check your math logic."

def validate_step(line_prev_str, line_curr_str):
    try:
        if not line_prev_str or not line_curr_str:
            return False, "Empty"

        # USE THE NEW UNIFIED EXTRACTOR
        correct_set = extract_values(line_prev_str)
        user_set = extract_values(line_curr_str)
        
        # If extraction failed (e.g. syntax garbage), return False
        if not correct_set and line_prev_str: 
            return False, "Syntax Error in Line A"
            
        # 1. Perfect Match
        if correct_set == user_set:
            return True, "Valid"
        
        # 2. Subset (Partial Credit)
        if user_set.issubset(correct_set) and len(user_set) > 0:
            return True, "Partial"
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v1.4", page_icon="🧮")
st.title("🧮 Step-Checker v1.4")

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
k1.button("x²", on_click=add_to_curr, args=("^2",)) # Updated to ^ for student familiarity
k2.button("±", on_click=add_to_curr, args=("+/-",)) 
k3.button("÷", on_click=add_to_curr, args=("/",))
k4.button("(", on_click=add_to_curr, args=("(",))
k5.button(")", on_click=add_to_curr, args=(")",))

st.markdown("---")

if st.button("Check Logic", type="primary"):
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    
    is_valid, status = validate_step(line_a, line_b)
    
    hint_message = ""
    if not is_valid:
        hint_message = diagnose_error(line_a, line_b)

    now = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.history.append({
        "Time": now,
        "Input A": line_a,
        "Input B": line_b,
        "Result": status,
        "Hint Given": hint_message
    })
    
    if is_valid and status == "Valid":
        st.success("✅ **Perfect Logic!**")
        st.balloons()
    elif is_valid and status == "Partial":
        st.warning("⚠️ **Technically Correct, but Incomplete.**")
        st.write("You found one valid solution, but you missed the other root.")
    else:
        st.error("❌ **Logic Break**")
        if hint_message:
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
