import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x**2 + 5 = 21"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""

# --- HELPER FUNCTIONS ---
def add_to_curr(text_to_add):
    st.session_state.line_curr += text_to_add

def pretty_print(math_str):
    """
    Converts raw Python math (x**2) into pretty LaTeX (x^2)
    using the SymPy engine itself.
    """
    try:
        if "=" in math_str:
            lhs, rhs = math_str.split("=")
            # Convert both sides to fancy math and put the '=' back
            lat_lhs = latex(sympify(lhs))
            lat_rhs = latex(sympify(rhs))
            return f"{lat_lhs} = {lat_rhs}"
        else:
            return latex(sympify(math_str))
    except:
        return None # Return nothing if the user is still typing incomplete math

def validate_step(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        def parse_eq(eq_str):
            if "=" in eq_str:
                lhs, rhs = eq_str.split("=")
                return Eq(sympify(lhs), sympify(rhs))
            else:
                return sympify(eq_str)

        eq1 = parse_eq(line_prev_str)
        eq2 = parse_eq(line_curr_str)
        
        if not line_prev_str or not line_curr_str:
            return False, "Empty Input"

        sol1 = solve(eq1, x)
        sol2 = solve(eq2, x)
        
        if sol1 == sol2:
            return True, "Valid"
        else:
            return False, "Invalid"
    except Exception as e:
        return False, f"Syntax Error: {e}"

def diagnose_error(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        # Same logic as before
        def parse_eq(eq_str):
            if "=" in eq_str:
                lhs, rhs = eq_str.split("=")
                return Eq(sympify(lhs), sympify(rhs))
            else:
                return sympify(eq_str)

        eq_prev = parse_eq(line_prev_str)
        eq_curr = parse_eq(line_curr_str)
        
        sol_prev = solve(eq_prev, x)
        sol_curr = solve(eq_curr, x)
        
        if not sol_prev or not sol_curr:
            return "Syntax error."
        
        val_prev = sol_prev[0]
        val_curr = sol_curr[0]
        diff = val_curr - val_prev
        
        if diff != 0:
            return "Check your operations. Did you add when you should have subtracted?"
        return "The math doesn't match."
    except Exception:
        return "Logic broken."

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v0.4", page_icon="🧮")
st.title("🧮 Step-Checker v0.4")
st.caption("Now with True LaTeX Rendering")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Previous Line")
    st.text_input("Line A", key="line_prev", label_visibility="collapsed")
    
    # NEW PREVIEW LOGIC
    if st.session_state.line_prev:
        pretty = pretty_print(st.session_state.line_prev)
        if pretty:
            st.latex(pretty)
        else:
            st.caption("Typing...")

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    
    # NEW PREVIEW LOGIC
    if st.session_state.line_curr:
        pretty = pretty_print(st.session_state.line_curr)
        if pretty:
            st.latex(pretty)
        else:
            st.caption("Typing...")

st.markdown("##### ⌨️ Quick Keys")
k1, k2, k3, k4, k5 = st.columns(5)
k1.button("x²", on_click=add_to_curr, args=("**2",))
k2.button("√x", on_click=add_to_curr, args=("sqrt(",))
k3.button("÷", on_click=add_to_curr, args=("/",))
k4.button("(", on_click=add_to_curr, args=("(",))
k5.button(")", on_click=add_to_curr, args=(")",))

st.markdown("---")

if st.button("Check Logic", type="primary"):
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    is_valid, message = validate_step(line_a, line_b)
    
    if is_valid:
        st.success("✅ **Logic Verified!**")
        st.balloons()
    else:
        hint = diagnose_error(line_a, line_b)
        st.error("❌ **Logic Break**")
        st.info(f"💡 {hint}")
