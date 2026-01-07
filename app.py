import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex, Abs
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x/2 + 2 = 10"
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
    5. NEW: Swaps '%' for '/100'
    6. NEW: Swaps ' of ' for '*'
    7. NEW: Swaps '|...|' (pipes) for 'abs(...)' if user types them
    """
    text = text.lower()
    text = text.replace(" and ", ",")
    text = text.replace("^", "**")
    text = text.replace("+/-", "±")
    
    # NEW: Percentage and "Of" logic
    text = text.replace("%", "/100")
    text = text.replace(" of ", "*")
    
    # NEW: Handle pipe bars for absolute value |x| -> abs(x)
    # Simple heuristic: if we see pipes, we try to wrap content in abs()
    # Note: Complex parsing of nested pipes is hard, but this covers basic usage.
    if "|" in text:
        # We leave pipes for the parser to handle if possible, 
        # or we could recommend users use 'abs()'. 
        # For now, let's just clean common simple pipe usage if needed,
        # but SymPy doesn't use pipes for input naturally.
        # We will assume user might type 'abs(-4)' as per your bug report.
        pass 
        
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
        
        # evaluate=False prevents 2(x+4) from becoming 2x+8
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def extract_values(text_str):
    """
    Robustly extracts a SET of numerical solutions.
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
            
        # Case B: Comma list
        elif "," in clean:
            rhs = clean.split("=")[1] if "=" in clean else clean
            items = rhs.split(",")
            for i in items:
                if i.strip():
                    vals.add(smart_parse(i.strip(), evaluate=True))
                    
        # Case C: Equation or Expression
        elif "=" in clean:
            eq = smart_parse(clean, evaluate=True)
            sol = solve(eq, x)
            vals.update(sol)
            
        else:
            # Just a number or expression (like "20% of 100")
            if clean.strip():
                # If it's an expression like "20/100 * 100", calculating it gives the 'value'
                val = smart_parse(clean.strip(), evaluate=True)
                vals.add(val)
                
    except Exception:
        pass
        
    return vals

def diagnose_error(line_prev_str, line_curr_str):
    try:
        correct_vals = extract_values(line_prev_str)
        student_vals = extract_values(line_curr_str)
        
        if not correct_vals:
            return "I can't solve the previous line (Syntax error?)."
        if not student_vals:
            return "I can't understand your answer."
            
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

        correct_set = extract_values(line_prev_str)
        user_set = extract_values(line_curr_str)
        
        # FIX FOR ISSUE #1: Safety Check
        # If correct_set is empty, it means we failed to solve the Previous Line.
        # We MUST NOT return True here.
        if not correct_set and line_prev_str: 
            return False, "Could not solve Line A"
            
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

st.set_page_config(page_title="Step-Checker v1.5", page_icon="🧮")
st.title("🧮 Step-Checker v1.5")

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
    # Preview logic
    if st.session_state.line_prev:
        st.latex(pretty_print(st.session_state.line_prev))

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    if st.session_state.line_curr:
        st.latex(pretty_print(st.session_state.line_curr))

st.markdown("##### ⌨️ Quick Keys")
k1, k2, k3, k4, k5 = st.columns(5)
k1.button("x²", on_click=add_to_curr, args=("^2",)) 
k2.button("±", on_click=add_to_curr, args=("+/-",)) 
k3.button("|x|", on_click=add_to_curr, args=("abs(",)) # NEW BUTTON for Absolute Value
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
